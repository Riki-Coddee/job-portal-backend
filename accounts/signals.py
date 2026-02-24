# accounts/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Update user activity on login"""
    User.objects.filter(id=user.id).update(
        last_activity=timezone.now(),
        is_online=True
    )

@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """Update user activity on logout"""
    if user:
        User.objects.filter(id=user.id).update(
            last_activity=timezone.now(),
            is_online=False
        )