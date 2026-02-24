# notifications/models.py
from django.db import models
from django.utils import timezone
from accounts.models import CustomUser, JobSeeker, Recruiter
from jobs.models import Job
from applications.models import Application, Interview

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('application_update', 'Application Update'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_reminder', 'Interview Reminder'),
        ('new_message', 'New Message'),
        ('job_recommendation', 'Job Recommendation'),
        ('application_status_change', 'Application Status Change'),
        ('offer_extended', 'Offer Extended'),
        ('system_alert', 'System Alert'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_url = models.CharField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Optional: Link to related objects
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    interview = models.ForeignKey(Interview, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['user', 'notification_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email}: {self.title}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def time_ago(self):
        """Human-readable time difference"""
        delta = timezone.now() - self.created_at
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    @property
    def icon(self):
        """Return appropriate icon name"""
        icon_map = {
            'application_update': 'briefcase',
            'interview_scheduled': 'calendar',
            'interview_reminder': 'clock',
            'new_message': 'message-circle',
            'job_recommendation': 'zap',
            'application_status_change': 'refresh-cw',
            'offer_extended': 'award',
            'system_alert': 'alert-circle',
        }
        return icon_map.get(self.notification_type, 'bell')