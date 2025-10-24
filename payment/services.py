import stripe
from django.conf import settings
from payment.models import Payment


def create_payment_session(borrowing):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    book = borrowing.book

    days = (borrowing.expected_return - borrowing.borrow_date).days
    total_amount = int(float(book.daily_fee) * days * 100)

    DOMAIN = settings.DOMAIN

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "USD",
                    "unit_amount": total_amount,
                    "product_data": {"name": book.title},
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

    payment = Payment.objects.create(
        borrowing=borrowing,
        type=Payment.Type.PAYMENT,
        status=Payment.PaymentStatus.PENDING,
        money_to_pay=total_amount / 100,
    )
    payment.session_id = checkout_session.id
    payment.session_url = checkout_session.url
    payment.save()

    return checkout_session.url
