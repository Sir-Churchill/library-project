from datetime import date

from django.db import transaction
from drf_spectacular.utils import (
    OpenApiResponse,
    OpenApiExample,
    extend_schema,
    OpenApiParameter,
    extend_schema_view,
)
from rest_framework import status, mixins, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
)
from payment.models import Payment
from payment.services import create_payment_session

FINE_MULTIPLE = 2


@extend_schema_view(
    list=extend_schema(
        summary="List borrowings",
        description=(
            "Returns a list of all borrowings.\n\n"
            "- Regular users see **only their own borrowings**.\n"
            "- Admins can filter by `user_id` and `is_active`.\n\n"
            "Parameters:\n"
            "- `user_id`: Comma-separated list of user IDs (admin only)\n"
            "- `is_active`: `true` for active borrowings (not yet returned), "
            "`false` for returned ones."
        ),
        parameters=[
            OpenApiParameter(
                name="user_id",
                description="Filter by user IDs (admin only)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="is_active",
                description="Filter by borrowing status (true/false)",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=BorrowingListSerializer,
                description="List of borrowings",
                examples=[
                    OpenApiExample(
                        "Example response",
                        value=[
                            {
                                "id": 1,
                                "book_title": "Django for Pros",
                                "borrow_date": "2025-10-01",
                                "expected_return": "2025-10-05",
                                "actual_return_date": None,
                            },
                            {
                                "id": 2,
                                "book_title": "Python Tricks",
                                "borrow_date": "2025-10-10",
                                "expected_return": "2025-10-20",
                                "actual_return_date": "2025-10-18",
                            },
                        ],
                    )
                ],
            ),
        },
    ),
    retrieve=extend_schema(
        summary="Retrieve borrowing details",
        description="Returns detailed information about a specific borrowing.",
        responses={
            200: OpenApiResponse(
                response=BorrowingDetailSerializer,
                examples=[
                    OpenApiExample(
                        "Borrowing detail",
                        value={
                            "id": 1,
                            "user": 5,
                            "book": {
                                "id": 10,
                                "title": "Clean Code",
                                "author": "Robert C. Martin",
                                "cover": "HARD",
                            },
                            "borrow_date": "2025-10-01",
                            "expected_return": "2025-10-10",
                            "actual_return_date": None,
                        },
                    ),
                ],
            ),
            404: OpenApiResponse(
                description="Borrowing not found",
                examples=[OpenApiExample("Not found", value={"detail": "Not found."})],
            ),
        },
    ),
    create=extend_schema(
        summary="Create new borrowing",
        description=(
            "Creates a new borrowing for the authenticated user.\n\n"
            "Decreases the book inventory by 1 and returns a Stripe payment URL "
            "for the borrowing fee.\n\n"
            "Raises an error if:\n"
            "- The book is out of stock\n"
            "- The user already has an active borrowing for the same book"
        ),
        request=BorrowingSerializer,
        responses={
            201: OpenApiResponse(
                response=BorrowingSerializer,
                description="Borrowing successfully created",
                examples=[
                    OpenApiExample(
                        "Created borrowing",
                        value={
                            "id": 1,
                            "user": 3,
                            "book": 5,
                            "borrow_date": "2025-10-25",
                            "expected_return": "2025-10-30",
                            "actual_return_date": None,
                            "payment_url": "https://checkout.stripe.com/pay/session_123",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Validation error",
                examples=[
                    OpenApiExample(
                        "Already borrowed",
                        value={"detail": "You already borrowed Django for Pros"},
                    ),
                    OpenApiExample(
                        "Out of stock",
                        value={"detail": "Django for Pros is out of stock"},
                    ),
                ],
            ),
        },
    ),
)
class BorrowingView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
):
    queryset = Borrowing.objects.all().select_related("book")
    serializer_class = BorrowingSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        elif self.action == "retrieve":
            return BorrowingDetailSerializer
        return BorrowingSerializer

    @staticmethod
    def _params_to_ints(qs):
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        queryset = self.queryset

        user_id = self.request.query_params.get("user_id")
        is_active = self.request.query_params.get("is_active")

        if self.request.user.is_staff:
            if user_id:
                user_ids = self._params_to_ints(user_id)
                queryset = queryset.filter(user__in=user_ids)

            if is_active:
                if is_active.lower() == "true":
                    queryset = queryset.filter(actual_return_date__isnull=True)
                elif is_active.lower() == "false":
                    queryset = queryset.filter(actual_return_date__isnull=False)

            return queryset

        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = BorrowingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book_id = request.data.get("book")
        book = Book.objects.select_for_update().get(id=book_id)

        with transaction.atomic():
            if Borrowing.objects.filter(
                user=request.user, book=book, actual_return_date__isnull=True
            ).exists():
                raise ValidationError(f"You already borrowed {book.title}")
            if book.inventory <= 0:
                raise ValidationError(f"{book.title} is out of stock")

            borrowing_instance = serializer.save(user=request.user, book=book)

            book.inventory -= 1
            book.save()

            payment_url = create_payment_session(borrowing_instance)

        response_data = BorrowingSerializer(borrowing_instance).data
        response_data["payment_url"] = payment_url

        return Response(response_data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.action in ["list", "retrieve", "create"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


def calculate_fine(borrowing):
    if borrowing.actual_return_date is None:
        return 0

    if borrowing.actual_return_date > borrowing.expected_return:
        days_overdue = (borrowing.actual_return_date - borrowing.expected_return).days
        fine_amount = days_overdue * borrowing.book.daily_fee * FINE_MULTIPLE
        return fine_amount
    return 0


@extend_schema(
    operation_id="return_borrowed_book",
    summary="Return borrowed book",
    description=(
        "Marks a borrowed book as returned. "
        "If the book is returned later than the expected date, "
        "a fine payment session will be created and returned in the response."
    ),
    request=None,
    responses={
        200: OpenApiResponse(
            response=BorrowingSerializer,
            description="Book successfully returned",
            examples=[
                OpenApiExample(
                    "Returned without fine",
                    value={
                        "id": 1,
                        "user": 3,
                        "book": 5,
                        "borrow_date": "2025-10-20",
                        "expected_return": "2025-10-23",
                        "actual_return_date": "2025-10-25",
                        "fine_payment_url": None,
                    },
                ),
                OpenApiExample(
                    "Returned with fine",
                    value={
                        "id": 1,
                        "user": 3,
                        "book": 5,
                        "borrow_date": "2025-10-10",
                        "expected_return": "2025-10-15",
                        "actual_return_date": "2025-10-25",
                        "fine_payment_url": "https://checkout.stripe.com/pay/session_12345",
                    },
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Book was already returned",
            examples=[
                OpenApiExample(
                    "Already returned",
                    value={"detail": "This book was returned"},
                ),
            ],
        ),
        404: OpenApiResponse(
            description="Borrowing not found",
            examples=[
                OpenApiExample(
                    "Borrowing not found",
                    value={"detail": "Not found."},
                ),
            ],
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def return_book(request, pk):
    borrowing = Borrowing.objects.select_for_update().get(pk=pk)
    book = borrowing.book

    if borrowing.actual_return_date is not None:
        return Response(
            {"detail": "This book was returned"}, status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        book.inventory += 1
        book.save()

        borrowing.actual_return_date = date.today()
        borrowing.save()

        fine_amount = calculate_fine(borrowing)
        fine_payment_url = None
        if fine_amount > 0:
            fine_payment = Payment.objects.create(
                borrowing=borrowing,
                type=Payment.Type.FINE,
                status=Payment.PaymentStatus.PENDING,
                money_to_pay=fine_amount,
            )
            fine_payment_url = create_payment_session(fine_payment.borrowing)

        serializer = BorrowingSerializer(borrowing)
        data = serializer.data
        if fine_payment_url:
            data["fine_payment_url"] = fine_payment_url

    return Response(data, status=status.HTTP_200_OK)
