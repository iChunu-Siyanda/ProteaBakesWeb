# The Structure:
user → who wrote the review.
product → what they reviewed.
order_item → proves the review is tied to an actual purchase.
OneToOneField on order_item → one purchased item can only receive one review.
rating → restricted to 1–5.
comment → optional written feedback.
status → allows moderation before publishing.

So the intended flow becomes:

Customer buys product
        ↓
OrderItem exists
        ↓
Customer submits review
        ↓
Review = PENDING
        ↓
Admin/moderation
        ↓
PUBLISHED
