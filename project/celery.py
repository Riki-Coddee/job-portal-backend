# project_name/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure the beat schedule
app.conf.beat_schedule = {
    # Interview reminders (every 6 hours)
    'send-interview-reminders': {
        'task': 'notifications.tasks.send_interview_reminders',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    # Job recommendations (daily at 9 AM)
    'generate-job-recommendations': {
        'task': 'notifications.tasks.generate_job_recommendations',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    # Profile reminders (daily at 10 AM)
    'send-profile-completion-reminders': {
        'task': 'notifications.tasks.send_profile_completion_reminders',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    # Cleanup (weekly on Sunday at 3 AM)
    'cleanup-old-notifications': {
        'task': 'notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
    },
    # Batch processing (optional)
    'process-notification-batch': {
        'task': 'notifications.tasks.process_notification_batch',
        'schedule': crontab(hour=8, minute=30),  # Daily at 8:30 AM
    },
}

# Optional: Task routing and other configurations
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)