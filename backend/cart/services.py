from django.db import transaction

from .models import Cart, CartItem
from catalog.models import Product
from inventory.services import assert_available


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

    existing = CartItem.objects.filter(cart=cart, product=product).first()
    assert_available(product, (existing.quantity if existing else 0) + quantity)

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

    assert_available(item.product, quantity)

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
    