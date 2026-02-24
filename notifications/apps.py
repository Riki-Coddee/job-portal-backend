# notifications/apps.py
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    
    def ready(self):
        # Import signals only after all models are loaded
        # Use try-except to handle cases during migration
        try:
            import notifications.signals
        except Exception as e:
            print(f"Note: Could not import notifications signals: {e}")
            print("This is normal during migrations.")