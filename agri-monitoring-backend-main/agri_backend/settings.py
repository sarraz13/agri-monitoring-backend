import os
from pathlib import Path
from datetime import timedelta
import dj_database_url
from dotenv import load_dotenv
load_dotenv()

# Build paths fel project
BASE_DIR = Path(__file__).resolve().parent.parent




# SECURITY SETTINGS
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = True
ALLOWED_HOSTS = [] #feragh khater juste localhost


# Applications
INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin', #interface admin
    "django.contrib.auth", #systeme d'auth
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework", #rest API framework
    'rest_framework_simplejwt',  # JWT authentication
    'monitoring', #main app
    'ml',#ml app
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be first for CORS
    "django.middleware.security.SecurityMiddleware",  # Security features
    "django.contrib.sessions.middleware.SessionMiddleware",  # Session handling
    "django.middleware.common.CommonMiddleware",  # URL processing
    "django.middleware.csrf.CsrfViewMiddleware",  # CSRF protection
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # User auth
    "django.contrib.messages.middleware.MessageMiddleware",  # Messages
    "django.middleware.clickjacking.XFrameOptionsMiddleware",  # Clickjacking protection
]

ROOT_URLCONF = "agri_backend.urls" #main urls conf

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True, #no templates (Angular frontend)
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "agri_backend.wsgi.application"




# Database (using env variables for security)
DATABASE_URL = os.getenv("DATABASE_URL")
#use URL wala kol variable wahadha
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    # Use individual environment variables
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
    
    # Validate that all required DB environment variables are set
    if not all([os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD")]):
        raise ValueError(
            "Database configuration is incomplete. "
            "Please set DATABASE_URL or DB_NAME, DB_USER, DB_PASSWORD environment variables."
        )

#
#STATIC & MEDIA FILES
STATIC_URL = "/static/"  # URL prefix for static files
STATIC_ROOT = BASE_DIR / "staticfiles"  # Where collectstatic puts files

MEDIA_URL = "/media/"  # URL prefix for media files
MEDIA_ROOT = BASE_DIR / "media"  # Where uploaded files are stored


# REST Framework Config
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",  #JWT Tokens
    ),
    "DEFAULT_PERMISSION_CLASSES": (   # Permission classes (applied to all views unless overridden)
        "rest_framework.permissions.IsAuthenticated",# Require login for all endpoints
    ),
}

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),  # Short-lived access token
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1), # Longer-lived refresh token
    "AUTH_HEADER_TYPES": ("Bearer",), # Authorization: Bearer <token>
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"  # Default language
TIME_ZONE = "UTC"  # Time zone for the database
USE_I18N = True  # Internationalization support
USE_TZ = True  # Time zone support



# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS Configuration
# Controls which domains can access the API
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",  # Angular default port
    "http://127.0.0.1:4200",  # Angular localhost
    "http://localhost:8080",  # Alternative port
]

CORS_ALLOW_CREDENTIALS = True # Allow cookies in CORS requests

# Allowed headers in CORS requests
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]