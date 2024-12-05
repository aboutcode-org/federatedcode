#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

import sys
from pathlib import Path

import environ

PROJECT_DIR = environ.Path(__file__) - 1
ROOT_DIR = PROJECT_DIR - 1


# Environment

ENV_FILE = "/etc/federatedcode/.env"
if not Path(ENV_FILE).exists():
    ENV_FILE = ROOT_DIR(".env")

env = environ.Env()
environ.Env.read_env(ENV_FILE)

# Security

SECRET_KEY = env.str("SECRET_KEY")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS", default=[".localhost", "127.0.0.1", "[::1]", "host.docker.internal"]
)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# SECURITY WARNING: don't run with debug turned on in production
DEBUG = env.bool("FEDERATEDCODE_DEBUG", default=False)

############################################
# Federation settings
AP_CONTENT_TYPE = "application/activity+json"

FEDERATEDCODE_LOG_LEVEL = env.str("FEDERATEDCODE_LOG_LEVEL", "INFO")

# Use False for development
FEDERATEDCODE_REQUIRE_AUTHENTICATION = env.bool(
    "FEDERATEDCODE_REQUIRE_AUTHENTICATION", default=True
)
# The DNS host, port and "domain"
FEDERATEDCODE_HOST = env.str("FEDERATEDCODE_HOST", "127.0.0.1")
FEDERATEDCODE_PORT = env.str("FEDERATEDCODE_PORT", "8000")
FEDERATEDCODE_DOMAIN = env.str("FEDERATEDCODE_DOMAIN", f"{FEDERATEDCODE_HOST}:{FEDERATEDCODE_PORT}")

# directory location of the workspace where we store Git repos and content
# default to var/ in current directory in development
FEDERATEDCODE_WORKSPACE_LOCATION = env.str("FEDERATEDCODE_WORKSPACE_LOCATION", "var")

# these do NOT have a default
FEDERATEDCODE_CLIENT_ID = env.str("FEDERATEDCODE_CLIENT_ID")
FEDERATEDCODE_CLIENT_SECRET = env.str("FEDERATEDCODE_CLIENT_SECRET")


# Application definition

INSTALLED_APPS = [
    # Local apps
    # Must come before Third-party apps for proper templates override
    "fedcode",
    # Django built-in
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.humanize",
    # Third-party apps
    "oauth2_provider",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # OAUTH
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
]

ROOT_URLCONF = "federatedcode.urls"

WSGI_APPLICATION = "federatedcode.wsgi.application"

SECURE_PROXY_SSL_HEADER = env.tuple(
    "SECURE_PROXY_SSL_HEADER", default=("HTTP_X_FORWARDED_PROTO", "https")
)

# Database

DATABASES = {
    "default": {
        "ENGINE": env.str("FEDERATEDCODE_DB_ENGINE", "django.db.backends.postgresql"),
        "HOST": env.str("FEDERATEDCODE_DB_HOST", "localhost"),
        "NAME": env.str("FEDERATEDCODE_DB_NAME", "federatedcode"),
        "USER": env.str("FEDERATEDCODE_DB_USER", "federatedcode"),
        "PASSWORD": env.str("FEDERATEDCODE_DB_PASSWORD", "federatedcode"),
        "PORT": env.str("FEDERATEDCODE_DB_PORT", "5432"),
        "ATOMIC_REQUESTS": True,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ],
        },
    },
]

# Passwords

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": env.int("FEDERATEDCODE_PASSWORD_MIN_LENGTH", default=12),
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Testing

# True if running tests through `./manage test` or `pytest`
IS_TESTS = any(t in sys.argv for t in ("test", "pytest"))

if IS_TESTS:
    import tempfile

    # Do not pollute the workspace while running the tests.
    FEDERATEDCODE_WORKSPACE_LOCATION = tempfile.mkdtemp()
    FEDERATEDCODE_REQUIRE_AUTHENTICATION = True
    # The default password hasher is rather slow by design.
    # Using a faster hashing algorithm in the testing context to speed up the run.
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]

# Debug toolbar

DEBUG_TOOLBAR = env.bool("FEDERATEDCODE_DEBUG_TOOLBAR", default=False)
if DEBUG and DEBUG_TOOLBAR:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["null"] if IS_TESTS else ["console"],
            "propagate": False,
        },
        # Set FEDERATEDCODE_LOG_LEVEL=DEBUG to display all SQL queries in the console.
        "django.db.backends": {
            "level": FEDERATEDCODE_LOG_LEVEL,
        },
        "fedcode.pipelines": {
            "handlers": ["null"] if IS_TESTS else ["console"],
            "level": FEDERATEDCODE_LOG_LEVEL,
            "propagate": False,
        },
    },
}

# Instead of sending out real emails the console backend just writes the emails
# that would be sent to the standard output.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = env.str("TIME_ZONE", default="UTC")

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"

STATIC_ROOT = env.str("STATIC_ROOT", default="/var/federatedcode/static/")

STATICFILES_DIRS = [
    PROJECT_DIR("static"),
]


# Django restframework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework.authentication.SessionAuthentication",
        # "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework.renderers.AdminRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env.int("FEDERATEDCODE_REST_API_PAGE_SIZE", default=50),
    "UPLOADED_FILES_USE_URL": False,
}


if not FEDERATEDCODE_REQUIRE_AUTHENTICATION:
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = ("rest_framework.permissions.AllowAny",)


OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "REFRESH_TOKEN_EXPIRE_SECONDS": 3600 * 24 * 365,
    "SCOPES": {"read": "Read scope", "write": "Write scope"},
}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "oauth2_provider.backends.OAuth2Backend",
)
