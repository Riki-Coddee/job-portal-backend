# notifications/utils.py
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count
from django.core.cache import cache
from .models import Notification

# Remove ANY lines that import from .utils like:
# from .utils import (create_application_notification, ...)

def create_notification(user, notification_type, title, message, **kwargs):
    """
    Create notification with rate limiting to prevent spam
    """
    # Rate limiting: Check if similar notification was created recently
    one_hour_ago = timezone.now() - timedelta(hours=1)
    similar_exists = Notification.objects.filter(
        user=user,
        notification_type=notification_type,
        title=title,
        created_at__gte=one_hour_ago
    ).exists()
    
    if similar_exists:
        return None  # Skip to prevent duplicate notifications
    
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=kwargs.get('action_url'),
        priority=kwargs.get('priority', 'medium'),
        application=kwargs.get('application'),
        interview=kwargs.get('interview'),
        job=kwargs.get('job'),
    )
    return notification

def create_application_notification(application, status_change=False):
    """Create notification for application updates"""
    if status_change:
        title = f'Application Status Updated: {application.job.title}'
        # Use get_status_display() instead of property
        status_display = dict(application.STATUS_CHOICES).get(application.status, application.status)
        message = f'Your application for "{application.job.title}" has been updated to {status_display}.'
        notification_type = 'application_status_change'
    else:
        title = f'Application Submitted: {application.job.title}'
        message = f'You have successfully applied for "{application.job.title}".'
        notification_type = 'application_update'
    
    return create_notification(
        user=application.seeker.user,
        notification_type=notification_type,
        title=title,
        message=message,
        application=application,
        action_url=f'/applications/my-applications/{application.id}/',
        priority='medium'
    )

def create_interview_notification(interview, is_reminder=False):
    """Create notification for interviews"""
    if is_reminder:
        title = f'Interview Reminder: {interview.application.job.title}'
        message = f'Reminder: Interview scheduled for {interview.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}'
        notification_type = 'interview_reminder'
        priority = 'high'
    else:
        title = f'Interview Scheduled: {interview.application.job.title}'
        message = f'Interview scheduled for {interview.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}'
        notification_type = 'interview_scheduled'
        priority = 'medium'
    
    return create_notification(
        user=interview.application.seeker.user,
        notification_type=notification_type,
        title=title,
        message=message,
        interview=interview,
        action_url=f'/applications/my-applications/{interview.application.id}/',
        priority=priority
    )

def create_message_notification(message, receiver):
    """Create notification for new messages"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Rate limiting
    one_hour_ago = timezone.now() - timedelta(hours=1)
    similar_exists = Notification.objects.filter(
        user=receiver,
        notification_type='new_message',
        created_at__gte=one_hour_ago
    ).exists()
    
    if similar_exists:
        return None
    
    sender_name = message.sender.get_full_name() or message.sender.email
    
    return create_notification(
        user=receiver,
        notification_type='new_message',
        title=f'New Message from {sender_name}',
        message=message.content[:100] + ('...' if len(message.content) > 100 else ''),
        action_url=f'/chat/conversations/{message.conversation.id}/',
        priority='medium'
    )

# Add this function for interview reminders
def check_and_create_interview_reminders():
    """Efficient check for upcoming interviews and create reminders"""
    from applications.models import Interview
    
    now = timezone.now()
    tomorrow = now + timedelta(hours=24)
    
    # Only check interviews in next 24 hours
    upcoming_interviews = Interview.objects.filter(
        status='scheduled',
        scheduled_date__range=[now, tomorrow],
        notification_reminder_sent=False
    ).select_related('application__seeker__user', 'application__job')[:100]
    
    notifications_created = 0
    interview_ids_to_update = []
    
    for interview in upcoming_interviews:
        # Check if reminder already exists (cached check)
        cache_key = f"interview_reminder_{interview.id}"
        if not cache.get(cache_key):
            notification = create_interview_notification(interview, is_reminder=True)
            if notification:
                cache.set(cache_key, True, timeout=3600)
                interview_ids_to_update.append(interview.id)
                notifications_created += 1
    
    # Bulk update to mark as reminder sent
    if interview_ids_to_update:
        Interview.objects.filter(id__in=interview_ids_to_update).update(
            notification_reminder_sent=True
        )
    
    return notifications_created

def generate_job_recommendations_for_user(user, limit=3):
    """Generate personalized job recommendations for a specific user"""
    from jobs.models import Job
    from accounts.models import JobSeeker
    
    try:
        seeker = JobSeeker.objects.get(user=user)
    except JobSeeker.DoesNotExist:
        return []
    
    # Get user skills
    user_skills = set(seeker.skills or [])
    
    if not user_skills:
        return []
    
    # Find jobs matching user skills
    jobs = Job.objects.filter(
        is_published=True,
        is_active=True,
        expires_at__gt=timezone.now()
    ).annotate(
        matching_skills_count=Count('skills', filter=Q(skills__in=user_skills))
    ).filter(
        matching_skills_count__gt=0
    ).order_by(
        '-matching_skills_count',
        '-is_featured',
        '-created_at'
    )[:limit]
    
    return jobs

def create_job_recommendation_notifications():
    """Create job recommendation notifications for active seekers"""
    from accounts.models import JobSeeker
    
    # Only process users active in last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    
    active_seekers = JobSeeker.objects.filter(
        user__last_login__gte=week_ago,
        user__is_active=True
    ).select_related('user')[:50]
    
    notifications_created = 0
    
    for seeker in active_seekers:
        # Check if already got recommendations recently
        last_recommendation = Notification.objects.filter(
            user=seeker.user,
            notification_type='job_recommendation',
            created_at__gte=timezone.now() - timedelta(days=1)
        ).exists()
        
        if last_recommendation:
            continue
        
        # Get recommendations
        recommended_jobs = generate_job_recommendations_for_user(seeker.user, limit=1)
        
        if recommended_jobs:
            job = recommended_jobs[0]
            notification = create_notification(
                user=seeker.user,
                notification_type='job_recommendation',
                title=f'Recommended Job: {job.title}',
                message=f'{job.company} is hiring for {job.title} in {job.location}.',
                job=job,
                action_url=f'/jobs/{job.id}/',
                priority='low'
            )
            if notification:
                notifications_created += 1
    
    return notifications_created

def send_profile_completion_reminders():
    """Send reminders to job seekers with incomplete profiles"""
    from accounts.models import JobSeeker
    
    # Define what makes a profile "complete"
    required_fields = ['skills', 'experience', 'education', 'resume']
    
    incomplete_seekers = JobSeeker.objects.filter(
        user__is_active=True,
        user__last_login__gte=timezone.now() - timedelta(days=30)
    ).exclude(
        # Exclude those who got reminder in last 7 days
        user__notifications__notification_type='system_alert',
        user__notifications__title__contains='Profile Completion',
        user__notifications__created_at__gte=timezone.now() - timedelta(days=7)
    )[:50]
    
    notifications_created = 0
    
    for seeker in incomplete_seekers:
        missing_fields = []
        
        # Check each required field
        for field in required_fields:
            field_value = getattr(seeker, field, None)
            if not field_value or (isinstance(field_value, list) and len(field_value) == 0):
                missing_fields.append(field.replace('_', ' ').title())
        
        if missing_fields:
            missing_list = ", ".join(missing_fields[:3])
            if len(missing_fields) > 3:
                missing_list += f" and {len(missing_fields) - 3} more"
            
            notification = create_notification(
                user=seeker.user,
                notification_type='system_alert',
                title='Complete Your Profile',
                message=f'Your profile is {100 - (len(missing_fields) * 20)}% complete. Add: {missing_list}.',
                action_url='/profile/edit/',
                priority='medium'
            )
            if notification:
                notifications_created += 1
    
    return notifications_created

def cleanup_old_notifications():
    """Remove old notifications to keep database clean"""
    month_ago = timezone.now() - timedelta(days=30)
    
    # Delete old read notifications
    deleted_count, _ = Notification.objects.filter(
        is_read=True,
        created_at__lt=month_ago
    ).delete()
    
    return deleted_count