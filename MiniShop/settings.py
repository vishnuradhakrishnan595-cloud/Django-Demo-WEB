"""
Django settings for MiniShop project.

Django version: 5.2.17
"""

from pathlib import Path
import os

from dotenv import load_dotenv


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

load_dotenv(BASE_DIR / ".env")


# =========================================================
# SECURITY
# =========================================================

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is missing from environment variables."
    )


DEBUG = os.getenv("DEBUG", "False").lower() == "true"


# =========================================================
# ALLOWED HOSTS
# =========================================================

ALLOWED_HOSTS = [
    "django-demo-web-1.onrender.com",
    "localhost",
    "127.0.0.1",
]


# =========================================================
# CSRF TRUSTED ORIGINS
# =========================================================

CSRF_TRUSTED_ORIGINS = [
    "https://django-demo-web-1.onrender.com",
]


# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [

    # -----------------------------------------------------
    # Django
    # -----------------------------------------------------

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # -----------------------------------------------------
    # Cloudinary
    # -----------------------------------------------------

    "cloudinary",
    "cloudinary_storage",

    # -----------------------------------------------------
    # MiniShop Apps
    # -----------------------------------------------------

    "Guest",
    "User",
    "Shop",

    # -----------------------------------------------------
    # Django Allauth
    # -----------------------------------------------------

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",

    # WhiteNoise for static files
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Django Allauth
    "allauth.account.middleware.AccountMiddleware",
]


# =========================================================
# URL CONFIGURATION
# =========================================================

ROOT_URLCONF = "MiniShop.urls"


# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [

    {
        "BACKEND":
            "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

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


# =========================================================
# WSGI
# =========================================================

WSGI_APPLICATION = "MiniShop.wsgi.application"


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")


if DATABASE_URL:

    import dj_database_url

    DATABASES = {

        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )

    }

else:

    DATABASES = {

        "default": {

            "ENGINE":
                "django.db.backends.sqlite3",

            "NAME":
                BASE_DIR / "db.sqlite3",
        }

    }


# =========================================================
# PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME":
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.MinimumLengthValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.CommonPasswordValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# Make sure this directory exists locally.
STATICFILES_DIRS = [
    BASE_DIR / "static",
]


# =========================================================
# STORAGE
# =========================================================

STORAGES = {

    # -----------------------------------------------------
    # User uploaded files → Cloudinary
    # -----------------------------------------------------

    "default": {

        "BACKEND":
            "cloudinary_storage.storage.MediaCloudinaryStorage",
    },

    # -----------------------------------------------------
    # CSS / JS / Static files → WhiteNoise
    # -----------------------------------------------------

    "staticfiles": {

        "BACKEND":
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# =========================================================
# CLOUDINARY
# =========================================================

CLOUDINARY_CLOUD_NAME = os.getenv(
    "CLOUDINARY_CLOUD_NAME"
)

CLOUDINARY_API_KEY = os.getenv(
    "CLOUDINARY_API_KEY"
)

CLOUDINARY_API_SECRET = os.getenv(
    "CLOUDINARY_API_SECRET"
)


# Make sure all Cloudinary variables exist

if not all([
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
]):

    raise RuntimeError(
        "Cloudinary environment variables are missing. "
        "Set CLOUDINARY_CLOUD_NAME, "
        "CLOUDINARY_API_KEY and "
        "CLOUDINARY_API_SECRET."
    )


CLOUDINARY_STORAGE = {

    "CLOUD_NAME":
        CLOUDINARY_CLOUD_NAME,

    "API_KEY":
        CLOUDINARY_API_KEY,

    "API_SECRET":
        CLOUDINARY_API_SECRET,
}


# =========================================================
# GOOGLE / DJANGO ALLAUTH
# =========================================================

SITE_ID = 1


# Normal Django login

LOGIN_REDIRECT_URL = "/user/"

LOGOUT_REDIRECT_URL = "/login/"


# Django Allauth

ACCOUNT_LOGIN_REDIRECT_URL = "/user/"

ACCOUNT_SIGNUP_REDIRECT_URL = "/user/"


# =========================================================
# GOOGLE LOGIN
# =========================================================

SOCIALACCOUNT_LOGIN_ON_GET = True


SOCIALACCOUNT_PROVIDERS = {

    "google": {

        "SCOPE": [
            "profile",
            "email",
        ],

        "AUTH_PARAMS": {

            "access_type":
                "online",
        },
    },
}


# =========================================================
# SESSION
# =========================================================

# 2 hours

SESSION_COOKIE_AGE = 7200

SESSION_SAVE_EVERY_REQUEST = True

SESSION_COOKIE_HTTPONLY = True


# =========================================================
# HTTPS / RENDER SECURITY
# =========================================================

if not DEBUG:

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

else:

    SESSION_COOKIE_SECURE = False

    CSRF_COOKIE_SECURE = False


# =========================================================
# LOGGING
# =========================================================

LOGGING = {

    "version": 1,

    "disable_existing_loggers": False,

    "handlers": {

        "console": {

            "class":
                "logging.StreamHandler",
        },
    },

    "loggers": {

        "django": {

            "handlers": [
                "console"
            ],

            "level":
                "ERROR",

            "propagate":
                False,
        },

        "django.server": {

            "handlers": [
                "console"
            ],

            "level":
                "ERROR",

            "propagate":
                False,
        },
    },
}


# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)