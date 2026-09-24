# The Flow:
Customer
   ↓
Checkout
   ↓
Django creates Order
   ↓
Django creates Payment
   ↓
Payment Provider
   ↓
Customer pays
   ↓
Provider → Webhook → Django
                         ↓
                  WebhookEvent
                         ↓
                  verify event
                         ↓
                  update Payment
                         ↓
                  update Order
                         ↓
                  Notification

WebhookEvent.event_id being unique gives us idempotency: if the provider sends the same webhook twice, we don't process the payment twice.
