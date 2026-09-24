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

The important part is that audit records survive even if the user account is deleted