"""
Django settings for the Protea Bakes backend.

Everything environment-specific is read from environment variables
(see .env.example). In local development, copy .env.example to .env;
it is loaded automatically if python-dotenv is installed.
"""

import os
import sys
from datetime import time, timedelta
from decimal import Decimal
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # optional: load backend/.env in local development
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


DEBUG = env_bool("DEBUG", False)
RUNNING_TESTS = "test" in sys.argv or "pytest" in sys.modules

# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or RUNNING_TESTS:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("SECRET_KEY environment variable is required.")

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,testserver" if (DEBUG or RUNNING_TESTS) else ""
)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Frontend (Next.js) origin(s), used for CORS and payment return URLs.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", FRONTEND_URL)

if not DEBUG and not RUNNING_TESTS:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------------------------------------------------------------------------
# Business configuration (all overridable through the environment)
# ---------------------------------------------------------------------------

PAYMENT_CURRENCY = "ZAR"

DELIVERY_FEE = Decimal(os.environ.get("DELIVERY_FEE", "50.00"))
# Orders with a subtotal at or above this get free delivery. Empty = never.
_free = os.environ.get("FREE_DELIVERY_THRESHOLD", "")
FREE_DELIVERY_THRESHOLD = Decimal(_free) if _free else None

BAKERY_TIME_ZONE = os.environ.get("BAKERY_TIME_ZONE", "Africa/Johannesburg")
PICKUP_MIN_LEAD_HOURS = int(os.environ.get("PICKUP_MIN_LEAD_HOURS", 24))
PICKUP_MAX_DAYS_AHEAD = int(os.environ.get("PICKUP_MAX_DAYS_AHEAD", 60))
PICKUP_OPEN_TIME = time.fromisoformat(os.environ.get("PICKUP_OPEN_TIME", "08:00"))
PICKUP_CLOSE_TIME = time.fromisoformat(os.environ.get("PICKUP_CLOSE_TIME", "17:00"))
# Python weekday numbers: Monday=0 ... Sunday=6. Default: closed Sundays.
PICKUP_CLOSED_WEEKDAYS = [int(d) for d in env_list("PICKUP_CLOSED_WEEKDAYS", "6")]
# Max pickup bookings per day. 0 = unlimited.
PICKUP_MAX_BOOKINGS_PER_DAY = int(os.environ.get("PICKUP_MAX_BOOKINGS_PER_DAY", 0))

# Unpaid orders are cancelled (and their stock released) after this long.
UNPAID_ORDER_EXPIRY_MINUTES = int(os.environ.get("UNPAID_ORDER_EXPIRY_MINUTES", 60))
# A PENDING payment older than this may be replaced by a fresh checkout.
PAYMENT_PENDING_TIMEOUT_MINUTES = int(os.environ.get("PAYMENT_PENDING_TIMEOUT_MINUTES", 30))

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

# "yoco" in production. The fake "test" provider (and its unauthenticated
# webhook endpoint) only exists in DEBUG / when running the test suite.
PAYMENT_TEST_PROVIDER_ENABLED = DEBUG or RUNNING_TESTS
PAYMENT_PROVIDER = os.environ.get(
    "PAYMENT_PROVIDER", "test" if PAYMENT_TEST_PROVIDER_ENABLED else "yoco"
)
if PAYMENT_PROVIDER == "test" and not PAYMENT_TEST_PROVIDER_ENABLED:
    raise ImproperlyConfigured("The 'test' payment provider cannot be used when DEBUG is off.")

YOCO_SECRET_KEY = os.environ.get("YOCO_SECRET_KEY", "")
YOCO_WEBHOOK_SECRET = os.environ.get("YOCO_WEBHOOK_SECRET", "")  # starts with whsec_
YOCO_API_BASE_URL = os.environ.get("YOCO_API_BASE_URL", "https://payments.yoco.com/api")
PAYMENT_WEBHOOK_TOLERANCE_SECONDS = 300

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",

    "users",
    "catalog",
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

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# REST framework / JWT
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("THROTTLE_ANON", "200/hour"),
        "user": os.environ.get("THROTTLE_USER", "2000/hour"),
        # Applied per-view through throttle_scope:
        "auth": os.environ.get("THROTTLE_AUTH", "20/hour"),
        "password_reset": os.environ.get("THROTTLE_PASSWORD_RESET", "5/hour"),
        "webhook": os.environ.get("THROTTLE_WEBHOOK", "600/hour"),
    },
}

if RUNNING_TESTS:
    # Throttle counters live in the cache and would leak between tests.
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()

SPECTACULAR_SETTINGS = {
    "TITLE": "Protea Bakes API",
    "DESCRIPTION": "Backend API for the Protea Bakes online bakery.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", 15))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# ---------------------------------------------------------------------------
# Database: PostgreSQL when DB_NAME is set, SQLite otherwise (local dev/tests)
# ---------------------------------------------------------------------------

if os.environ.get("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", 60)),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-za"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Protea Bakes <orders@proteabakes.co.za>")

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "users.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
