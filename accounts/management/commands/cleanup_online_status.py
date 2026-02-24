# accounts/management/commands/cleanup_online_status.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Clean up stale online statuses'

    def handle(self, *args, **options):
        # Mark users as offline if they haven't been active in 10 minutes
        threshold = timezone.now() - timedelta(minutes=10)
        
        updated = User.objects.filter(
            is_online=True,
            last_activity__lt=threshold
        ).update(is_online=False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully marked {updated} users as offline')
        )