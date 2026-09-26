# Purpose of Audt section:
The audit section is your backend's history/tracking system. It records important actions so you can later answer: what happened, to which object, when, and by whom?

For Protea Bakes, examples would be:

ORDER_CREATED → Order 123
ORDER_STATUS_CHANGED → Order 123, PENDING → CONFIRMED
PAYMENT_SUCCEEDED → Payment 456
INVENTORY_RESTOCKED → Product 789
PROMOTION_REDEEMED → Promotion SAVE10
USER_UPDATED → User 42

The important distinction is that audit logs are not ordinary customer data. Your services create them; they're primarily useful for debugging, accountability, administration, and investigating unexpected changes.

# Audit Captures The Following:
User:        admin@proteabakes.co.za
Action:      ORDER_STATUS_CHANGED
Model:       Order
Object:      1042
Details:     {"old": "PREPARING", "new": "READY"}
IP:          192.168.1.10

Or:

Action: PAYMENT_REFUNDED
Model: Payment
Object: 87

The important part is that audit records survive even if the user account is deleted.

audit logs are generally system-generated, so I would not expose a public endpoint that lets customers create arbitrary audit logs. We'll expose read access for authenticated users, while creation remains a service-layer operation used by your backend.

# Build:

GET /api/audit/ — authenticated user's audit logs
GET /api/audit/object/<model_name>/<object_id>/ — logs for a specific object
