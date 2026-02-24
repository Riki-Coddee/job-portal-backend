"""
ASGI config for project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

if os.environ.get('RENDER'):  # Render sets this to 'true' for all services
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.deployment_settings')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# settings_module = 'project.deployment_settings' if 'RENDER_EXTERNAL_HOSTNAME' in os.environ else 'project.settings'
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

application = get_asgi_application()
