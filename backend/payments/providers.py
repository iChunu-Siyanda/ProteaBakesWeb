"""
Payment provider layer.

A provider turns an Order into a hosted checkout the customer is redirected
to, and verifies the signed webhooks the provider sends back. Adding another
provider (PayFast, Ozow, ...) means adding one class here and registering it
in ``get_provider``.
"""

import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal

import requests
from django.conf import settings


class ProviderError(Exception):
    """The provider rejected a request or could not be reached."""


class WebhookVerificationError(Exception):
    """A webhook failed signature/timestamp verification."""


def to_cents(amount):
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


class FakePaymentProvider:
    """Fake provider for local development and the test suite only."""

    name = "test"

    def create_payment(self, *, order):
        return {
            "provider_reference": f"TEST-{order.order_number}",
            "checkout_url": f"https://example.com/pay/{order.order_number}",
        }


class YocoProvider:
    """
    Yoco online Checkout API (hosted redirect flow).

    - Checkout: POST {base}/checkouts, amount in cents, returns id + redirectUrl.
    - Webhooks: Standard-Webhooks style HMAC-SHA256 signature over
      "{webhook-id}.{webhook-timestamp}.{raw body}" using the base64-decoded
      secret (without the "whsec_" prefix).
    """

    name = "yoco"
    MIN_AMOUNT = Decimal("2.00")

    def create_payment(self, *, order):
        if not settings.YOCO_SECRET_KEY:
            raise ProviderError("Yoco is not configured.")

        if Decimal(order.total) < self.MIN_AMOUNT:
            raise ProviderError("Yoco cannot process payments below R2.00.")

        base = f"{settings.FRONTEND_URL}/orders/{order.order_number}"
        body = {
            "amount": to_cents(order.total),
            "currency": settings.PAYMENT_CURRENCY,
            "successUrl": f"{base}/payment/success",
            "cancelUrl": f"{base}/payment/cancelled",
            "failureUrl": f"{base}/payment/failed",
            "metadata": {"orderNumber": order.order_number},
        }

        try:
            response = requests.post(
                f"{settings.YOCO_API_BASE_URL}/checkouts",
                json=body,
                headers={"Authorization": f"Bearer {settings.YOCO_SECRET_KEY}"},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError("Could not create the Yoco checkout.") from exc

        checkout_id = data.get("id")
        redirect_url = data.get("redirectUrl")
        if not checkout_id or not redirect_url:
            raise ProviderError("Unexpected response from Yoco.")

        return {"provider_reference": checkout_id, "checkout_url": redirect_url}

    @staticmethod
    def verify_webhook(*, headers, raw_body, now=None):
        secret = settings.YOCO_WEBHOOK_SECRET
        if not secret:
            raise WebhookVerificationError("Webhook secret is not configured.")

        webhook_id = headers.get("webhook-id")
        timestamp = headers.get("webhook-timestamp")
        signature_header = headers.get("webhook-signature")

        if not (webhook_id and timestamp and signature_header):
            raise WebhookVerificationError("Missing webhook signature headers.")

        try:
            sent_at = int(timestamp)
        except ValueError as exc:
            raise WebhookVerificationError("Invalid webhook timestamp.") from exc

        current = int(now if now is not None else time.time())
        if abs(current - sent_at) > settings.PAYMENT_WEBHOOK_TOLERANCE_SECONDS:
            raise WebhookVerificationError("Webhook timestamp outside tolerance.")

        try:
            key = base64.b64decode(secret.removeprefix("whsec_"))
        except ValueError as exc:
            raise WebhookVerificationError("Invalid webhook secret.") from exc

        signed = f"{webhook_id}.{timestamp}.".encode() + raw_body
        expected = base64.b64encode(
            hmac.new(key, signed, hashlib.sha256).digest()
        ).decode()

        # Header holds space-separated "v1,<signature>" entries.
        for part in signature_header.split(" "):
            _, _, candidate = part.partition(",")
            if candidate and hmac.compare_digest(expected, candidate):
                try:
                    return json.loads(raw_body)
                except ValueError as exc:
                    raise WebhookVerificationError("Invalid JSON body.") from exc

        raise WebhookVerificationError("Signature mismatch.")


def get_provider(name=None):
    name = name or settings.PAYMENT_PROVIDER

    if name == "yoco":
        return YocoProvider()

    if name == "test":
        if not settings.PAYMENT_TEST_PROVIDER_ENABLED:
            raise ProviderError("The test payment provider is disabled.")
        return FakePaymentProvider()

    raise ProviderError(f"Unknown payment provider: {name}")
