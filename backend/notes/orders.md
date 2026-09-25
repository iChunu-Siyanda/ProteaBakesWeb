# Checkout/order service:

Cart
 ↓
Validate cart
 ↓
Calculate subtotal
 ↓
Apply promotion (when present)
 ↓
Calculate delivery fee
 ↓
Calculate final total
 ↓
Create Order
 ↓
Create OrderItems with price snapshots
 ↓
Create fulfillment record
 ↓
Convert/clear cart
