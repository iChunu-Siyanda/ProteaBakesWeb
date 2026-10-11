import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditLog
from catalog.models import Category, Product
from orders.models import Order
from payments.models import Payment, WebhookEvent
from payments.providers import (
    ProviderError,
    WebhookVerificationError,
    YocoProvider,
    get_provider,
)
from payments.services import initiate_payment, process_payment_webhook
from users.models import User

SECRET_BYTES = b"super-secret-test-key"
WEBHOOK_SECRET = "whsec_" + base64.b64encode(SECRET_BYTES).decode()


def sign(webhook_id, timestamp, body):
    signed = f"{webhook_id}.{timestamp}.".encode() + body
    digest = hmac.new(SECRET_BYTES, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def make_order(user, total="500.00", number="PB-YOCO000001"):
    return Order.objects.create(
        user=user,
        order_number=number,
        fulfillment_type=Order.FulfillmentType.PICKUP,
        subtotal=total,
        discount_amount="0.00",
        delivery_fee="0.00",
        total=total,
    )


@override_settings(YOCO_SECRET_KEY="sk_test_123", FRONTEND_URL="https://shop.example")
class YocoCreateCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="c@example.com", password="securepassword123"
        )
        self.order = make_order(self.user, total="123.45")

    @mock.patch("payments.providers.requests.post")
    def test_creates_checkout_with_amount_in_cents(self, post):
        post.return_value.json.return_value = {
            "id": "ch_abc",
            "redirectUrl": "https://c.yoco.com/ch_abc",
        }

        result = YocoProvider().create_payment(order=self.order)

        self.assertEqual(result["provider_reference"], "ch_abc")
        self.assertEqual(result["checkout_url"], "https://c.yoco.com/ch_abc")

        _, kwargs = post.call_args
        self.assertEqual(kwargs["json"]["amount"], 12345)
        self.assertEqual(kwargs["json"]["currency"], "ZAR")
        self.assertEqual(kwargs["json"]["metadata"], {"orderNumber": "PB-YOCO000001"})
        self.assertTrue(kwargs["json"]["successUrl"].startswith("https://shop.example/"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk_test_123")

    @mock.patch("payments.providers.requests.post")
    def test_network_failure_becomes_provider_error(self, post):
        import requests

        post.side_effect = requests.ConnectionError("boom")

        with self.assertRaises(ProviderError):
            YocoProvider().create_payment(order=self.order)

    def test_rejects_amounts_below_r2(self):
        self.order.total = Decimal("1.50")

        with self.assertRaises(ProviderError):
            YocoProvider().create_payment(order=self.order)

    @override_settings(YOCO_SECRET_KEY="")
    def test_requires_configuration(self):
        with self.assertRaises(ProviderError):
            YocoProvider().create_payment(order=self.order)


class ProviderSelectionTests(TestCase):
    @override_settings(PAYMENT_TEST_PROVIDER_ENABLED=False)
    def test_test_provider_is_blocked_when_disabled(self):
        with self.assertRaises(ProviderError):
            get_provider("test")

    def test_unknown_provider(self):
        with self.assertRaises(ProviderError):
            get_provider("nope")


@override_settings(YOCO_WEBHOOK_SECRET=WEBHOOK_SECRET)
class YocoWebhookTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="c@example.com", password="securepassword123"
        )
        self.order = make_order(self.user, total="500.00")
        self.payment = Payment.objects.create(
            order=self.order,
            provider="yoco",
            provider_reference="ch_123",
            amount="500.00",
            currency="ZAR",
            status=Payment.Status.PENDING,
        )
        self.url = reverse("payment-webhook-yoco")

    def event(self, event_id="evt_1", amount=50000, currency="ZAR", checkout="ch_123"):
        return {
            "id": event_id,
            "type": "payment.succeeded",
            "payload": {
                "id": "p_1",
                "type": "payment",
                "amount": amount,
                "currency": currency,
                "status": "succeeded",
                "metadata": {"checkoutId": checkout},
            },
        }

    def send(self, event, timestamp=None, signature=None, webhook_id="msg_1"):
        body = json.dumps(event).encode()
        timestamp = str(int(timestamp if timestamp is not None else time.time()))
        return self.client.generic(
            "POST",
            self.url,
            data=body,
            content_type="application/json",
            HTTP_WEBHOOK_ID=webhook_id,
            HTTP_WEBHOOK_TIMESTAMP=timestamp,
            HTTP_WEBHOOK_SIGNATURE=signature or sign(webhook_id, timestamp, body),
        )

    def test_valid_event_confirms_order(self):
        response = self.send(self.event())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
        self.assertTrue(WebhookEvent.objects.get(event_id="evt_1").processed)
        self.assertTrue(
            AuditLog.objects.filter(action="PAYMENT_SUCCEEDED").exists()
        )

    def test_forged_signature_is_rejected(self):
        response = self.send(self.event(), signature="v1,bm90LXRoZS1yZWFsLXNpZw==")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertFalse(WebhookEvent.objects.exists())

    def test_missing_signature_headers_are_rejected(self):
        response = self.client.post(self.url, self.event(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stale_timestamp_is_rejected(self):
        response = self.send(self.event(), timestamp=time.time() - 3600)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_amount_mismatch_does_not_confirm_order(self):
        response = self.send(self.event(amount=100))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertTrue(AuditLog.objects.filter(action="PAYMENT_AMOUNT_MISMATCH").exists())

    def test_currency_mismatch_is_rejected(self):
        response = self.send(self.event(currency="USD"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_checkout_is_rejected(self):
        response = self.send(self.event(checkout="ch_unknown"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_event_is_idempotent(self):
        self.send(self.event())
        response = self.send(self.event(), webhook_id="msg_2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WebhookEvent.objects.filter(event_id="evt_1").count(), 1)
        self.assertEqual(
            AuditLog.objects.filter(action="PAYMENT_SUCCEEDED").count(), 1
        )

    def test_unknown_event_types_are_acknowledged(self):
        event = {"id": "evt_other", "type": "something.else", "payload": {}}
        response = self.send(event)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(WebhookEvent.objects.get(event_id="evt_other").processed)

    def test_payment_for_cancelled_order_flags_refund(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save()

        response = self.send(self.event())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertTrue(AuditLog.objects.filter(action="REFUND_REQUIRED").exists())

    @override_settings(YOCO_WEBHOOK_SECRET="")
    def test_unconfigured_secret_rejects_everything(self):
        with self.assertRaises(WebhookVerificationError):
            YocoProvider.verify_webhook(headers={}, raw_body=b"{}")


class TestProviderEndpointGateTests(APITestCase):
    @override_settings(PAYMENT_TEST_PROVIDER_ENABLED=False)
    def test_fake_webhook_is_404_outside_development(self):
        response = self.client.post(
            reverse("payment-webhook"),
            {"provider_reference": "TEST-1", "status": "succeeded"},
            format="json",
            HTTP_X_WEBHOOK_EVENT_ID="evt-1",
            HTTP_X_WEBHOOK_EVENT_TYPE="payment.updated",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PaymentRetryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="c@example.com", password="securepassword123"
        )
        self.order = make_order(self.user, number="PB-RETRY00001")
        self.provider = get_provider("test")

    def test_failed_payment_can_be_retried(self):
        payment, _ = initiate_payment(
            user=self.user, order_id=self.order.id, provider=self.provider
        )
        process_payment_webhook(
            provider="test",
            event_id="evt-fail",
            event_type="payment.updated",
            payload={"provider_reference": payment.provider_reference, "status": "failed"},
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)

        retried, _ = initiate_payment(
            user=self.user, order_id=self.order.id, provider=self.provider
        )

        self.assertEqual(retried.pk, payment.pk)
        self.assertEqual(retried.status, Payment.Status.PENDING)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)

    def test_paid_order_cannot_be_paid_again(self):
        payment, _ = initiate_payment(
            user=self.user, order_id=self.order.id, provider=self.provider
        )
        process_payment_webhook(
            provider="test",
            event_id="evt-ok",
            event_type="payment.updated",
            payload={"provider_reference": payment.provider_reference, "status": "succeeded"},
        )

        with self.assertRaises(ValueError):
            initiate_payment(
                user=self.user, order_id=self.order.id, provider=self.provider
            )

    @override_settings(PAYMENT_PENDING_TIMEOUT_MINUTES=0)
    def test_abandoned_pending_payment_can_be_replaced(self):
        payment, _ = initiate_payment(
            user=self.user, order_id=self.order.id, provider=self.provider
        )
        Payment.objects.filter(pk=payment.pk).update(
            created_at=payment.created_at.replace(year=2020)
        )

        retried, _ = initiate_payment(
            user=self.user, order_id=self.order.id, provider=self.provider
        )

        self.assertEqual(retried.pk, payment.pk)
