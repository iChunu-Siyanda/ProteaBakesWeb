from django.db import transaction

from .models import Cart, CartItem
from catalog.models import Product


@transaction.atomic
def get_or_create_active_cart(user):
    cart, _ = Cart.objects.get_or_create(
        user=user,
        status=Cart.Status.ACTIVE,
    )
    return cart


@transaction.atomic
def add_item_to_cart(user, product_id, quantity):
    cart = get_or_create_active_cart(user)

    product = Product.objects.get(
        id=product_id,
        is_active=True,
    )

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity},
    )

    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity"])

    return item


@transaction.atomic
def update_cart_item(user, item_id, quantity):
    cart = get_or_create_active_cart(user)

    item = CartItem.objects.get(
        id=item_id,
        cart=cart,
    )

    item.quantity = quantity
    item.save(update_fields=["quantity"])

    return item


@transaction.atomic
def remove_cart_item(user, item_id):
    cart = get_or_create_active_cart(user)

    item = CartItem.objects.get(
        id=item_id,
        cart=cart,
    )

    item.delete()
    