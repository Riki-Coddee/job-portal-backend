# notifications/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

# Track old status for comparison
application_status_cache = {}

@receiver(pre_save, sender='applications.Application')
def cache_application_status(sender, instance, **kwargs):
    """Cache old application status before save"""
    if instance.pk:
        try:
            # Lazy import
            from applications.models import Application
            old_instance = Application.objects.get(pk=instance.pk)
            application_status_cache[instance.pk] = old_instance.status
        except Exception:
            application_status_cache[instance.pk] = None

@receiver(post_save, sender='applications.Application')
def notify_application_status_change(sender, instance, created, **kwargs):
    """Notify when application is created or status changes"""
    # Lazy import inside the function to avoid circular imports
    from notifications.utils import create_application_notification
    
    if created:
        # New application
        transaction.on_commit(
            lambda: create_application_notification(instance, status_change=False)
        )
    else:
        # Check if status changed
        old_status = application_status_cache.get(instance.pk)
        if old_status is not None and old_status != instance.status:
            transaction.on_commit(
                lambda: create_application_notification(instance, status_change=True)
            )
    
    # Clean up cache
    if instance.pk in application_status_cache:
        del application_status_cache[instance.pk]

@receiver(post_save, sender='applications.Interview')
def notify_interview_scheduled(sender, instance, created, **kwargs):
    """Notify when interview is scheduled"""
    if created and instance.status == 'scheduled':
        # Lazy import
        from notifications.utils import create_interview_notification
        transaction.on_commit(
            lambda: create_interview_notification(instance, is_reminder=False)
        )

@receiver(post_save, sender='chat.Message')
def notify_new_message(sender, instance, created, **kwargs):
    """Notify when new message is received"""
    if created and not instance.is_system_message:
        # Lazy import
        from notifications.utils import create_message_notification
        transaction.on_commit(
            lambda: create_message_notification(instance, instance.receiver)
        )