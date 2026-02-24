# jobs/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Job

@shared_task
def publish_scheduled_jobs():
    """Publish jobs that have reached their scheduled date"""
    now = timezone.now()
    
    jobs_to_publish = Job.objects.filter(
        publish_option='schedule',
        scheduled_date__lte=now,
        is_published=False
    )
    
    for job in jobs_to_publish:
        job.is_published = True
        job.published_at = now
        job.save(update_fields=['is_published', 'published_at'])
    
    return f"Published {len(jobs_to_publish)} jobs"