# Create ProteaBakes Initial Folder:
ProteaBakes/
├── backend/
└── frontend/

# Create Django Project:
cd backend
python -m venv venv
If Windows PowerShell: .\venv\Scripts\Activate.ps1
If Linux/WSL: source venv/bin/activate
pip install django djangorestframework
django-admin startproject config .
Then verify: python manage.py runserver

# The models:
User -> customer account: User -> [Cart(1->1),Orders(1->many),Bookings(1->many),Notifications(1->many)]
Product -> baked goods being sold
Cart -> user's active shopping cart: Cart -> [CartItem(1->many)]
CartItem -> product + quantity inside a cart: CartItem -> [Product(1->many)]
Order -> completed order/purchase: Order -> [OrderItem(1→many),Payment(1→1),User(many->1)]
OrderItem -> product + quantity + price at time of purchase: OrderItem ->[Product(1->many)]
Booking -> pickup/order booking info: Booking -> [User(many->1)]
Payment -> payment transaction associated with an order
Notifications -> notify users

Create the models:
python manage.py startapp users
python manage.py startapp products
python manage.py startapp cart
python manage.py startapp orders
python manage.py startapp payments
python manage.py startapp catalog
python manage.py startapp notifications

# Register All Apps In config/settings.py:
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",

    "users",
    "catalog",
    "products",
    "cart",
    "orders",
    "payments",
    "notifications",
    "fulfillment",
    "inventory",
    "promotions",
    "reviews",
    "audit",
]

Then to verify: python manage.py check

# Create The Models:
For users: Add AUTH_USER_MODEL = "users.User" to cinfig/settings.py

Then migrate:
python manage.py makemigrations users
python manage.py migrate

# Create Super User:
python manage.py createsuperuser
Email: ...@gmail.com
First name: Siyanda
Last name: Mchunu
Password: 
Password (again): 
Superuser created successfully.

# Verify If All Models are Logically Correct:
Then run python manage.py makemigrations, and python manage.py showmigrations to inspect the database.
The inspect Django itself: python manage.py check
