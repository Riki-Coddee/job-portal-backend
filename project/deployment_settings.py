import os
import dj_database_url
from .settings import *
from .settings import BASE_DIR

ALLOWED_HOSTS=[os.environ.get('RENDER_EXTERNAL_HOSTNAME')]
CSRF_TRUSTED_ORIGINS = ['https://'+os.environ.get('RENDER_EXTERNAL_HOSTNAME')]

DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'accounts.middleware.UpdateLastActivityMiddleware',
]

# CORS_ALLOWED_ORIGINS = [
#     'http://localhost:5173'
# ]

STORAGES= {
    "default" : {
        "BACKEND" : "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles" : {
        "BACKEND":"whitenoise.storage.CompressedStaticFilesStorage"
    },
}

DATABASES = {
    "default":dj_database_url.config(
        default = os.environ.get("DATABASE_URL"),
        conn_max_age = 600
    )
}


# ========== EMAIL CONFIGURATION FOR RENDER FREE TIER ==========
# Using SendGrid Web API (HTTPS/443) instead of SMTP (587) 
# because Render free tier blocks SMTP ports

import sendgrid
from sendgrid.helpers.mail import Mail

# SendGrid API configuration (works on free tier - port 443)
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')  # Required

# Email sender and recipient settings
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

# Site URL for email templates
SITE_URL = os.environ.get('SITE_URL')

# Custom email sending function using SendGrid Web API
def send_email_via_sendgrid(subject, message, from_email, recipient_list, html_message=None):
    """
    Send email using SendGrid Web API (works on Render free tier)
    Returns True if successful, False otherwise
    """
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
        return response.status_code == 202  # 202 means accepted
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"SendGrid email failed: {e}")
        return False

# Override Django's send_mail to use SendGrid API
from django.core.mail import send_mail as django_send_mail
from django.core.mail import EmailMessage

def send_mail(subject, message, from_email, recipient_list, 
              fail_silently=False, auth_user=None, auth_password=None, 
              connection=None, html_message=None):
    """
    Replacement for django.core.mail.send_mail that uses SendGrid API
    """
    return send_email_via_sendgrid(subject, message, from_email, recipient_list, html_message)