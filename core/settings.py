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

# Local dev: default True. Production: set DEBUG=False in the environment.
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

if not DEBUG:
    _env_sk = os.environ.get('DJANGO_SECRET_KEY', '')
    if not _env_sk or _env_sk.startswith('django-insecure'):
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            'When DEBUG is False, set a strong DJANGO_SECRET_KEY in the environment '
            '(not the default insecure key).'
        )

_raw_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,10.0.2.2')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()]

# Application definition
INSTALLED_APPS = [
    'corsheaders',
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
    'corsheaders.middleware.CorsMiddleware',
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
# - Development: SQLite (default). Leave DATABASE_URL unset.
# - Production: set DATABASE_URL to a PostgreSQL URI (Supabase, Neon, Railway, etc.).
#   Dependencies: dj-database-url + psycopg (see requirements.txt). Then: migrate.
# - Managed Postgres often appends ?sslmode=require (or sslmode=require) to the URI; keep it.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(
                DATABASE_URL,
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
# How many dated backup files to keep per type (db_*.sqlite3, pg_*.dump, data_*.json); oldest deleted after each run.
_raw_backup_keep = os.environ.get('GSO_BACKUP_KEEP', '7').strip()
try:
    GSO_BACKUP_KEEP = max(1, min(100, int(_raw_backup_keep)))
except ValueError:
    GSO_BACKUP_KEEP = 7

# CORS: dev defaults + optional production origins (comma-separated)
_cors_extra = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
if _cors_extra:
    CORS_ALLOWED_ORIGINS.extend([o.strip() for o in _cors_extra.split(',') if o.strip()])
CORS_ALLOW_ALL_ORIGINS = DEBUG

# CSRF: comma-separated HTTPS origins in production, e.g. https://gso.school.edu
_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '').strip()
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    if os.environ.get('USE_TLS_BEHIND_PROXY', '').lower() in ('true', '1', 'yes'):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True

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

# App version check (for mobile). Set GSO_APP_MIN_VERSION to force update (e.g. '1.1.0').
GSO_APP_MIN_VERSION = os.environ.get('GSO_APP_MIN_VERSION', '1.0.0')

# Logging (Part 1.3)
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'gso.log'),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
