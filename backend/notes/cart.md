# In Cart Models:
OneToOneField:
user = models.OneToOneField(...)
means one customer has one active cart.

# PROTECT:
PROTECT on Product means we can't delete a product that's referenced by a cart item.

# This constraint:
models.UniqueConstraint(
    fields=["cart", "product"],
    name="unique_product_per_cart",
)

prevents:
Cart 1
├── Chocolate Cake × 2
└── Chocolate Cake × 3

instead:
Cart 1
└── Chocolate Cake × 5   