import stripe
from rest_framework import viewsets, status
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from borrowings.models import Borrowing
from library_project import settings
from payment.models import Payment
from payment.serializers import (
    PaymentSerializer,
    PaymentListSerializer,
    PaymentDetailSerializer,
)


class PaymentGenericView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return PaymentListSerializer
        if self.action == "retrieve":
            return PaymentDetailSerializer
        return PaymentSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        if self.request.user.is_authenticated:
            return Payment.objects.filter(borrowing__user=self.request.user)
        return Payment.objects.none()


class PaymentCheckoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        borrowing_id = self.kwargs["borrowing_id"]
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            borrowing = Borrowing.objects.get(id=borrowing_id)
        except Borrowing.DoesNotExist:
            return Response(
                {"detail": "Borrowing not found"}, status=status.HTTP_404_NOT_FOUND
            )

        book = borrowing.book

        days = max(1, (borrowing.expected_return - borrowing.borrow_date).days)

        DOMAIN = settings.DOMAIN

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "USD",
                        "unit_amount": int(float(book.daily_fee) * days * 100),
                        "product_data": {
                            "name": book.title,
                        },
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{DOMAIN}/api/payments/success/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{DOMAIN}/api/payments/cancel/?session_id={{CHECKOUT_SESSION_ID}}",
            metadata={
                "borrowing_id": str(borrowing.id),
                "user_id": str(borrowing.user.id),
            },
        )

        Payment.objects.create(
            status=Payment.PaymentStatus.PENDING,
            type=Payment.Type.PAYMENT,
            borrowing=borrowing,
            session_url=checkout_session.url,
            session_id=checkout_session.id,
            money_to_pay=book.daily_fee * days,
        )

        return Response(
            {"session_id": checkout_session.id, "url": checkout_session.url}
        )


class PaymentSuccessView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "No session id"}, status=400)
        session = stripe.checkout.Session.retrieve(session_id)
        borrowing_id = session.metadata["borrowing_id"]
        user_id = session.metadata["user_id"]
        payment = Payment.objects.filter(session_id=session_id).first()
        if payment:
            payment.status = Payment.PaymentStatus.PAID
            payment.save()
        return Response(
            {
                "detail": "Success",
                "borrowing_id": str(borrowing_id),
                "user_id": str(user_id),
            }
        )


class PaymentCanceledView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "No session id"}, status=400)
        return Response(
            {
                "detail": "Canceled",
            }
        )
