import stripe
from django.conf import settings
from payment.models import Payment


def create_payment_session(borrowing):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    book = borrowing.book

    days = (borrowing.expected_return - borrowing.borrow_date).days
    total_amount = book.daily_fee * days

    DOMAIN = settings.DOMAIN

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "USD",
                    "unit_amount": total_amount,
                    "product_data": {
                        "name": book.title,
                    },
                },
                "quantity": 1,
            },
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
        money_to_pay=total_amount,
    )

    return checkout_session.url
