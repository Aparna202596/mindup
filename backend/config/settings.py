from pathlib import Path
import os
from dotenv import load_dotenv
from django.contrib.messages import constants as messages
from decouple import config
# ==============================================================================
# 1. INITIALIZATION & CORE PATHS
# ==============================================================================
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'


# ==============================================================================
# 2. SECURITY & ENVIRONMENT CONFIGURATION
# ==============================================================================
SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = []


# ==============================================================================
# 3. APPLICATION DEFINITIONS (Django, Third-Party, Local)
# ==============================================================================
INSTALLED_APPS = [
    # Core Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.sites',  

    # Third-Party Frameworks & Utilities
    'rest_framework',
    'django_filters',
    'crispy_forms',
    'crispy_bootstrap5',

    # Authentication (django-allauth)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Local Project Apps
    'apps.core',
    'apps.dashboard',
]


# ==============================================================================
# 4. MIDDLEWARE
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Allauth middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==============================================================================
# 5. TEMPLATES & CRISPY FORMS
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# ==============================================================================
# 6. DATABASE CONFIGURATION
# ==============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================================================================
# 7. AUTHENTICATION & USER CUSTOMIZATION
# ==============================================================================
AUTH_USER_MODEL = "core.CustomUser"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==============================================================================
# 8. DJANGO-ALLAUTH SPECIFIC SETTINGS
# ==============================================================================
SITE_ID = 2

# Resolved warning conflicts: using email as the primary identification method
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
# Disable username field and make email the unique identifier
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# Registration adjustments
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_LOGIN_ON_GET = True

# Flow Redirects
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Override admin login template
LOGIN_REDIRECT_URL = "smart-login-redirect"  
LOGOUT_REDIRECT_URL = "/"
# ==============================================================================
# 9. INTERNATIONALIZATION & LOCALIZATION
# ==============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ==============================================================================
# 10. STATIC & MEDIA FILE MANAGEMENT
# ==============================================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# STATIC_ROOT = BASE_DIR / "staticfiles" # Uncomment for deployment

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# 11. MESSAGES FRAMEWORK CONFIGURATION
# ==============================================================================    
MESSAGE_TAGS = {
    messages.DEBUG: 'info',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}
# ==============================================================================
# 12. SOCIAL ACCOUNT PROVIDERS (django-allauth)
# ==============================================================================
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "MANAGED": True,
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_SECRET"),
            "key": "",
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        }
    }
}