"""
Seed demo data for local development.

    python manage.py seed_demo
    python manage.py seed_demo --password "SomethingStrong-123"

Safe to run more than once: products, categories and the promo code are
updated in place, stock is only set the first time, and users are only created
if they don't exist (existing passwords are never changed).

Refuses to run when DEBUG is off unless you pass --force.
"""

'''
Categories and products: 5 categories and 15 products with South African bakery items (milk tart, koeksisters, vetkoek, rusks, hertzoggies, plus cakes, breads and pastries), with prices in rand. That is the top of your 12 to 18 range, so delete any you don’t want.
Stock: Normal products start with stock. The custom celebration cake and the koeksisters are made to order, so they have no stock limit.
Promo code: WELCOME10 gives 10% off and is valid for a year.
Users: A staff account, staff@proteabakes.local, and a customer, customer@example.com. Both use the default password ChangeMe-12345!, or pass your own with --password "...".
'''    

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalog.models import Category, Product
from inventory.models import InventoryItem
from inventory.services import restock_inventory
from promotions.models import Promotion
from users.models import User

CATEGORIES = [
    ("Cakes", "cakes"),
    ("Breads", "breads"),
    ("Pastries", "pastries"),
    ("Tarts & Traditional", "tarts-traditional"),
    ("Biscuits & Rusks", "biscuits-rusks"),
]

# (category slug, name, slug, sku, price, description, made_to_order, stock)
PRODUCTS = [
    ("cakes", "Chocolate Fudge Cake", "chocolate-fudge-cake", "CAKE-001", "320.00",
     "Rich three-layer chocolate cake with fudge icing. Serves 10 to 12.", False, 6),
    ("cakes", "Carrot Cake", "carrot-cake", "CAKE-002", "290.00",
     "Spiced carrot cake with cream cheese frosting and toasted pecans.", False, 6),
    ("cakes", "Red Velvet Cake", "red-velvet-cake", "CAKE-003", "340.00",
     "Classic red velvet with vanilla cream cheese frosting.", False, 5),
    ("cakes", "Lemon Drizzle Loaf", "lemon-drizzle-loaf", "CAKE-004", "120.00",
     "Zesty lemon loaf with a crisp sugar glaze.", False, 10),
    ("cakes", "Custom Celebration Cake", "custom-celebration-cake", "CAKE-005", "550.00",
     "Made to order for birthdays and special occasions. Add your design "
     "ideas in the order notes.", True, 0),
    ("breads", "Sourdough Loaf", "sourdough-loaf", "BRD-001", "65.00",
     "Slow-fermented white sourdough with a crackly crust.", False, 12),
    ("breads", "Seed Loaf", "seed-loaf", "BRD-002", "70.00",
     "Wholewheat loaf packed with sunflower, pumpkin and flax seeds.", False, 12),
    ("pastries", "Cinnamon Rolls (6 pack)", "cinnamon-rolls-6", "PST-001", "150.00",
     "Soft rolls with cinnamon sugar and vanilla glaze.", False, 10),
    ("pastries", "Buttermilk Scones (6 pack)", "buttermilk-scones-6", "PST-002", "90.00",
     "Light scones, best with jam and cream.", False, 12),
    ("pastries", "Chocolate Brownies (box of 9)", "chocolate-brownies-9", "PST-003", "135.00",
     "Fudgy brownies with a crackly top.", False, 12),
    ("tarts-traditional", "Milk Tart (Melktert)", "milk-tart", "TRD-001", "110.00",
     "Traditional cinnamon-dusted milk tart.", False, 8),
    ("tarts-traditional", "Koeksisters (12 pack)", "koeksisters-12", "TRD-002", "120.00",
     "Syrupy plaited koeksisters, made fresh to order.", True, 0),
    ("tarts-traditional", "Vetkoek (6 pack)", "vetkoek-6", "TRD-003", "80.00",
     "Golden fried dough, ready to fill with mince or jam.", False, 10),
    ("biscuits-rusks", "Buttermilk Rusks (500g)", "buttermilk-rusks-500g", "RSK-001", "85.00",
     "Crunchy rusks, perfect for dunking in your morning coffee.", False, 20),
    ("biscuits-rusks", "Hertzoggies (box of 12)", "hertzoggies-12", "RSK-002", "105.00",
     "Jam-filled shortcrust tartlets with a coconut meringue top.", False, 10),
]

LOW_STOCK_THRESHOLD = 3


class Command(BaseCommand):
    help = "Create demo categories, products, stock, a promo code and test users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="ChangeMe-12345!",
            help="Password for the demo staff and customer accounts (new accounts only).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running when DEBUG is off.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to seed demo data while DEBUG is off. Use --force if you mean it."
            )

        categories = self.seed_categories()
        self.seed_products(categories)
        self.seed_promotion()
        self.seed_users(options["password"])

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("  Staff:    staff@proteabakes.local")
        self.stdout.write("  Customer: customer@example.com")
        self.stdout.write(f"  Password: {options['password']} (for newly created accounts)")
        self.stdout.write("  Promo:    WELCOME10 (10% off)")

    def seed_categories(self):
        result = {}
        for name, slug in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "is_active": True},
            )
            result[slug] = category
        return result

    def seed_products(self, categories):
        for cat_slug, name, slug, sku, price, description, made_to_order, stock in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": categories[cat_slug],
                    "name": name,
                    "sku": sku,
                    "price": Decimal(price),
                    "description": description,
                    "is_active": True,
                    "is_made_to_order": made_to_order,
                },
            )

            if made_to_order:
                continue

            item, created = InventoryItem.objects.get_or_create(
                product=product,
                defaults={"quantity": 0, "low_stock_threshold": LOW_STOCK_THRESHOLD},
            )
            # Only set stock the first time so reruns never reset real numbers.
            if created:
                restock_inventory(
                    product_id=product.id,
                    quantity=stock,
                    reference="seed_demo",
                    notes="Initial demo stock",
                )

    def seed_promotion(self):
        now = timezone.now()
        Promotion.objects.update_or_create(
            code="WELCOME10",
            defaults={
                "name": "Welcome 10% off",
                "discount_type": Promotion.DiscountType.PERCENTAGE,
                "discount_value": Decimal("10.00"),
                "minimum_order_amount": Decimal("0.00"),
                "starts_at": now - timedelta(days=1),
                "expires_at": now + timedelta(days=365),
                "usage_limit": None,
                "is_active": True,
            },
        )

    def seed_users(self, password):
        if not User.objects.filter(email="staff@proteabakes.local").exists():
            User.objects.create_user(
                email="staff@proteabakes.local",
                password=password,
                first_name="Bakery",
                last_name="Staff",
                is_staff=True,
            )

        if not User.objects.filter(email="customer@example.com").exists():
            User.objects.create_user(
                email="customer@example.com",
                password=password,
                first_name="Demo",
                last_name="Customer",
                phone_number="0821234567",
            )
        