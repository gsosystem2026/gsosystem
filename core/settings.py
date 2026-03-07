"""
Django settings for GSO (General Services Office) project.
Phase 1.1: Project setup with Supabase (PostgreSQL) and .env for secrets.
"""
import os
from pathlib import Path

# Load .env if python-dotenv is installed (Phase 1.1)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-me-in-production-use-env'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # API
    'rest_framework',
    'rest_framework_simplejwt',
    'apps.gso_api',
    # GSO apps (all gso_*)
    'apps.gso_accounts',
    'apps.gso_requests',
    'apps.gso_units',
    'apps.gso_inventory',
    'apps.gso_reports',
    'apps.gso_notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.gso_accounts.context_processors.requestor_notifications',
                'apps.gso_accounts.context_processors.requestor_profile_form',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
# - Development: SQLite (default). No DATABASE_URL needed.
# - Production / Supabase: set DATABASE_URL in .env to PostgreSQL URI.
#   Then: pip install dj-database-url "psycopg[binary]" && python manage.py migrate
# Django uses the same schema on both; switching is just config.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    except ImportError:
        raise ImportError(
            'DATABASE_URL is set but dj-database-url is not installed. '
            'Run: pip install dj-database-url "psycopg[binary]"'
        )
else:
    # Default: SQLite for local development. Safe to migrate to PostgreSQL later.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-ph'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').is_dir() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media (uploaded files) — served via view with permission check; MEDIA_ROOT for storage
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Phase 1.2: custom user with roles
AUTH_USER_MODEL = 'gso_accounts.User'

# Auth redirects (overridden in login view for role-based redirect)
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'  # fallback
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Password reset: in development, emails are printed to the console.
# Set EMAIL_BACKEND and SMTP in production (e.g. SendGrid, Gmail).
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)

# Phase 8.3: App version for "new version available" prompt (bump on deploy)
GSO_APP_VERSION = os.environ.get('GSO_APP_VERSION', '1.0')

# Phase 9.1: Backup directory for gso_backup command (default: project_root/backups)
GSO_BACKUP_DIR = os.environ.get('GSO_BACKUP_DIR')

# REST API — for external system integration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
