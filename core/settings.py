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


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('true', '1', 'yes', 'on')


def _env_list(name: str, default_csv: str = '') -> list[str]:
    raw = os.environ.get(name, default_csv)
    return [item.strip() for item in raw.split(',') if item.strip()]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-me-in-production-use-env'
)

# Safe-by-default: require explicit DEBUG=True for local development.
DEBUG = _env_bool('DEBUG', False)

if not DEBUG:
    _env_sk = os.environ.get('DJANGO_SECRET_KEY', '')
    if not _env_sk or _env_sk.startswith('django-insecure'):
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            'When DEBUG is False, set a strong DJANGO_SECRET_KEY in the environment '
            '(not the default insecure key).'
        )

# Local defaults are only applied in DEBUG mode.
_default_allowed_hosts = 'localhost,127.0.0.1,10.0.2.2' if DEBUG else ''
ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', _default_allowed_hosts)

# Application definition
INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Auth: social login (Google OAuth)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
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
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Media (uploaded files) — served via view with permission check; MEDIA_ROOT for storage
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Phase 1.2: custom user with roles
AUTH_USER_MODEL = 'gso_accounts.User'
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Auth redirects (overridden in login view for role-based redirect)
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'  # fallback
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Allauth account behavior
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_ADAPTER = 'apps.gso_accounts.adapters.GSOSocialAccountAdapter'

# Google OAuth app credentials (set in .env)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': GOOGLE_OAUTH_CLIENT_ID,
            'secret': GOOGLE_OAUTH_CLIENT_SECRET,
            'key': '',
        },
    }
}

# Password reset: in development, emails are printed to the console.
# Set EMAIL_BACKEND and SMTP in production (e.g. SendGrid, Gmail).
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
# SMTP (used when EMAIL_BACKEND is smtp backend)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = _env_bool('EMAIL_USE_SSL', False)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@gso.local')
GSO_SITE_URL = os.environ.get('GSO_SITE_URL', '')
GSO_EMAIL_NOTIFICATIONS_ENABLED = _env_bool('GSO_EMAIL_NOTIFICATIONS_ENABLED', True)
GSO_PASSWORD_RESET_OTP_EXP_MINUTES = int(os.environ.get('GSO_PASSWORD_RESET_OTP_EXP_MINUTES', '10'))
GSO_PASSWORD_RESET_OTP_MAX_ATTEMPTS = int(os.environ.get('GSO_PASSWORD_RESET_OTP_MAX_ATTEMPTS', '5'))
GSO_PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS = int(
    os.environ.get('GSO_PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS', '60')
)
# Max upload size for request attachments (MB).
GSO_MAX_REQUEST_ATTACHMENT_MB = int(os.environ.get('GSO_MAX_REQUEST_ATTACHMENT_MB', '5'))
# Request attachment storage backend:
# - local (default): use MEDIA_ROOT filesystem
# - gdrive: upload request attachments to Google Drive
GSO_REQUEST_ATTACHMENT_STORAGE = os.environ.get('GSO_REQUEST_ATTACHMENT_STORAGE', 'local').strip().lower()
GSO_GDRIVE_FOLDER_ID = os.environ.get('GSO_GDRIVE_FOLDER_ID', '').strip()
GSO_GDRIVE_SERVICE_ACCOUNT_FILE = os.environ.get('GSO_GDRIVE_SERVICE_ACCOUNT_FILE', '').strip()
GSO_GDRIVE_SERVICE_ACCOUNT_JSON = os.environ.get('GSO_GDRIVE_SERVICE_ACCOUNT_JSON', '').strip()
# Invitation / password-reset token lifetime (used by Django token generator).
# Default 24 hours for account invitation links.
PASSWORD_RESET_TIMEOUT = int(os.environ.get('GSO_INVITE_LINK_TIMEOUT_SECONDS', '86400'))

# Phase 8.3: App version for "new version available" prompt (bump on deploy)
GSO_APP_VERSION = os.environ.get('GSO_APP_VERSION', '1.0')
GSO_LEGACY_MIGRATION_PERSONNEL_USERNAME = os.environ.get(
    'GSO_LEGACY_MIGRATION_PERSONNEL_USERNAME',
    'migrated_legacy',
).strip()

# Phase 9.1: Backup directory for gso_backup command (default: project_root/backups)
GSO_BACKUP_DIR = os.environ.get('GSO_BACKUP_DIR')
# How many dated backup files to keep per type (db_*.sqlite3, pg_*.dump, data_*.json); oldest deleted after each run.
_raw_backup_keep = os.environ.get('GSO_BACKUP_KEEP', '7').strip()
try:
    GSO_BACKUP_KEEP = max(1, min(100, int(_raw_backup_keep)))
except ValueError:
    GSO_BACKUP_KEEP = 7

# CORS: safe by default in production, local convenience only in DEBUG.
_default_cors_origins = 'http://localhost:3000,http://127.0.0.1:3000' if DEBUG else ''
CORS_ALLOWED_ORIGINS = _env_list('CORS_ALLOWED_ORIGINS', _default_cors_origins)
CORS_ALLOW_ALL_ORIGINS = _env_bool('CORS_ALLOW_ALL_ORIGINS', False if not DEBUG else False)

# CSRF: comma-separated HTTPS origins in production, e.g. https://gso.school.edu
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS', '')

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'same-origin'
    # HTTPS and cookie security defaults for production.
    SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = _env_bool('CSRF_COOKIE_HTTPONLY', False)
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
    SECURE_HSTS_PRELOAD = _env_bool('SECURE_HSTS_PRELOAD', True)
    if _env_bool('USE_TLS_BEHIND_PROXY', False):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# REST API — for external system integration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.environ.get('DRF_THROTTLE_ANON', '60/minute'),
        'user': os.environ.get('DRF_THROTTLE_USER', '300/minute'),
        'auth_token': os.environ.get('DRF_THROTTLE_AUTH_TOKEN', '10/minute'),
        'auth_refresh': os.environ.get('DRF_THROTTLE_AUTH_REFRESH', '30/minute'),
        'notification_write': os.environ.get('DRF_THROTTLE_NOTIFICATION_WRITE', '60/minute'),
    },
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

# On Windows dev runs, rotating file lock can break startup.
# Keep file logging for non-debug environments.
if DEBUG:
    LOGGING['root']['handlers'] = ['console']
    LOGGING['root']['level'] = 'INFO'
    LOGGING['loggers']['django']['handlers'] = ['console']
    LOGGING['loggers']['django']['level'] = 'INFO'
    LOGGING['loggers']['django.request']['handlers'] = ['console']
