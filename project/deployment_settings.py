import os
import dj_database_url
from .settings import *

# Override only what's necessary for production
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")

# Hosts
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS = [RENDER_EXTERNAL_HOSTNAME, 'localhost', '127.0.0.1']
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']
else:
    ALLOWED_HOSTS = ['*']
    CSRF_TRUSTED_ORIGINS = []

# CORS – restrict to your frontend domain in production
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOW_ALL_ORIGINS = False

# Middleware – keep only one of each, and ensure WhiteNoise is early
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.UpdateLastActivityMiddleware',
]

# Remove debug toolbar in production
if DEBUG:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INSTALLED_APPS.append('debug_toolbar')

# Static files – use manifest storage for cache busting
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Database
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True
    )
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Email – override the SMTP settings with SendGrid Web API
import sendgrid
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
if SENDGRID_API_KEY:
    # We'll use a custom email function, not Django's SMTP backend
    def send_mail(subject, message, from_email, recipient_list,
                  fail_silently=False, auth_user=None, auth_password=None,
                  connection=None, html_message=None):
        """Send email via SendGrid Web API (works on Render free tier)."""
        try:
            sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
            mail = Mail(
                from_email=from_email,
                to_emails=recipient_list[0] if recipient_list else None,
                subject=subject,
                plain_text_content=message
            )
            if html_message:
                mail.add_content(html_message, "text/html")
            response = sg.send(mail)
            return response.status_code == 202
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"SendGrid email failed: {e}")
            return False

    # Optionally replace Django's send_mail globally (use with caution)
    import django.core.mail
    django.core.mail.send_mail = send_mail

# Email sender settings
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
SITE_URL = os.environ.get('SITE_URL')

# Security enhancements for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True