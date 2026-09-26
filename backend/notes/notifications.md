# Notifications:
Order confirmation
Payment successful/failed
Order being prepared
Ready for pickup
Out for delivery
Delivered
Booking confirmation/reminder
Promotional notifications


# Four endpoints:

GET /api/notifications/ — user's notifications
POST /api/notifications/<id>/read/ — mark as read
GET /api/notifications/preferences/ — get/create preferences
PATCH /api/notifications/preferences/ — update preferences
