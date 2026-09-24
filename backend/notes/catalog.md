catalog = products + categories

# For Product Images:
pip install Pillow

# We're using on_delete=models.PROTECT:
for Product → Category.
That means you can't accidentally delete a category while products still depend on it.

# Slugs (For URLS):
A slug is a URL-friendly version of a name.

For example:

Product name:
Chocolate Birthday Cake

slug:
chocolate-birthday-cake

# sku (for your business/inventory system):
SKU = Stock Keeping Unit.

It's an internal identifier for a product.

For example:

Product: Chocolate Birthday Cake
SKU: CAKE-CHOC-001

Another:

Product: Vanilla Cupcakes
SKU: CUP-VAN-001

# Class Meta:
Meta is Django's way of specifying metadata/configuration for a model.

class Meta:
    ordering = ["position"]

This tells Django:
Whenever I retrieve ProductImage objects, sort them by position by default

