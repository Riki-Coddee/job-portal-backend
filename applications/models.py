# applications/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from accounts.models import Recruiter, JobSeeker
from jobs.models import Job

class Application(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
        ('withdrawn', 'Withdrawn')
    ]

    # Basic fields
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    seeker = models.ForeignKey(JobSeeker, on_delete=models.CASCADE, related_name="my_applications")
    resume_snapshot = models.FileField(upload_to="application_resumes/", null=True, blank=True, help_text="Resume used at time of application")
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    applied_at = models.DateTimeField(auto_now_add=True)
    
    # Application-specific data
    skills = models.JSONField(default=list, blank=True, 
                             help_text="Skills with ratings in this application")
    
    # Match scoring and rating
    match_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="AI/Manual match score (0-100)"
    )
    
    # Additional information from application form
    additional_info = models.JSONField(default=dict, blank=True,
                                      help_text="Additional application info like driving license, etc.")
    
    # Activity tracking
    last_active = models.DateTimeField(null=True, blank=True, 
                                      help_text="When the candidate was last active on platform")
    last_viewed = models.DateTimeField(null=True, blank=True,
                                      help_text="When recruiter last viewed this application")
    
    # REMOVED: interview_scheduled, interview_completed, interview_notes
    # These should be handled by the separate Interview model
    
    # Offer details
    offer_made = models.BooleanField(default=False)
    offer_date = models.DateTimeField(null=True, blank=True)
    offer_details = models.JSONField(default=dict, blank=True,
                                    help_text="Offer details like salary, start date, etc.")
    
    # Recruiter notes and rating
    recruiter_notes = models.TextField(blank=True)
    recruiter_rating = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Recruiter's rating (1-5 stars)"
    )
    
    # Communication tracking
    messages_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Flags
    is_favorite = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    hired_date = models.DateTimeField(null=True, blank=True, 
                                  help_text="Date when candidate was officially hired")

    class Meta:
        unique_together = ('job', 'seeker')
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['status', '-applied_at']),
            models.Index(fields=['match_score', '-applied_at']),
            models.Index(fields=['job', 'status']),
        ]

    def __str__(self):
        return f"{self.seeker.user.email} -> {self.job.title}"
    
    def mark_as_hired(self, hired_date=None):
        """Mark application as hired with date"""
        self.status = 'hired'
        self.hired_date = hired_date or timezone.now()
        self.save()
    
    def save(self, *args, **kwargs):
        """Handle resume file management"""
        # Delete old file if updating resume
        try:
            old_instance = Application.objects.get(pk=self.pk)
            if old_instance.resume_snapshot and old_instance.resume_snapshot != self.resume_snapshot:
                # Delete the old file
                old_instance.resume_snapshot.delete(save=False)
        except Application.DoesNotExist:
            pass
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete the associated resume file when deleting the application"""
        # Delete the resume file if it exists
        if self.resume_snapshot:
            # Check if file exists in storage
            if self.resume_snapshot.name and self.resume_snapshot.storage.exists(self.resume_snapshot.name):
                self.resume_snapshot.delete(save=False)
        
        # Now delete the application
        super().delete(*args, **kwargs)
    
    @property
    def get_status_display(self):
        """Return human-readable status with proper capitalization"""
        status_map = {
            'new': 'New',
            'pending': 'Pending',
            'reviewed': 'Reviewed',
            'shortlisted': 'Shortlisted',
            'interview': 'Interview',
            'offer': 'Offer',
            'rejected': 'Rejected',
            'accepted': 'Accepted',
            'hired' : 'Hired'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def candidate_name(self):
        """Get candidate full name"""
        return f"{self.seeker.user.first_name} {self.seeker.user.last_name}"
    
    @property
    def candidate_email(self):
        """Get candidate email"""
        return self.seeker.user.email
    
    @property
    def candidate_phone(self):
        """Get candidate phone from profile"""
        return self.seeker.phone_number or 'Not specified'
    
    @property
    def candidate_location(self):
        """Get candidate location from profile"""
        return self.seeker.location or 'Not specified'
    
    @property
    def position_applied(self):
        """Get job title"""
        return self.job.title
    
    @property
    def skill_summary(self):
        """Get skill summary with ratings"""
        if not self.skills:
            return "No skills rated"
        
        rated_skills = [skill for skill in self.skills if skill.get('rating', 0) > 0]
        if not rated_skills:
            return "No skills rated"
        
        # Get top 3 highest rated skills
        sorted_skills = sorted(rated_skills, key=lambda x: x.get('rating', 0), reverse=True)
        top_skills = sorted_skills[:3]
        
        summary = ", ".join([f"{skill['name']} ({skill.get('rating', 0)}/5)" for skill in top_skills])
        if len(rated_skills) > 3:
            summary += f" +{len(rated_skills) - 3} more"
        
        return summary
    
    # ADDED: Interview-related properties
    @property
    def has_scheduled_interview(self):
        """Check if application has a scheduled interview"""
        return self.interviews.filter(status='scheduled').exists()
    
    @property
    def next_interview(self):
        """Get the next scheduled interview"""
        return self.interviews.filter(status='scheduled').order_by('scheduled_date').first()
    
    @property
    def interview_scheduled(self):
        """Get scheduled interview datetime (for backward compatibility)"""
        interview = self.next_interview
        return interview.scheduled_date if interview else None
    
    @property
    def interview_completed(self):
        """Check if any interview is completed"""
        return self.interviews.filter(status='completed').exists()
    
    @property
    def interview_notes(self):
        """Get all interview feedback"""
        interviews = self.interviews.filter(status='completed')
        return "\n\n".join([f"{i.scheduled_date}: {i.feedback}" for i in interviews if i.feedback])   

class ApplicationNote(models.Model):
    """Notes added by recruiters on applications"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="notes")
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.application.candidate_name}"

class Interview(models.Model):
    """Interview scheduling and details"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    scheduled_date = models.DateTimeField()
    interview_type = models.CharField(max_length=50, choices=[
        ('phone', 'Phone Screen'),
        ('video', 'Video Call'),
        ('onsite', 'On-site Interview'),
        ('technical', 'Technical Assessment'),
    ])
    duration = models.PositiveIntegerField(help_text="Duration in minutes", default=60)
    meeting_link = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ], default='scheduled')
    feedback = models.TextField(blank=True)
    rating = models.PositiveIntegerField(
        null=True, blank=True, 
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    # Add recruiter field to track who scheduled the interview
    scheduled_by = models.ForeignKey(
        Recruiter, 
        on_delete=models.CASCADE,
        related_name='scheduled_interviews'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notification_reminder_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['scheduled_date']
        indexes = [
            models.Index(fields=['status', 'scheduled_date', 'notification_reminder_sent']),
        ]
    
    def __str__(self):
        return f"Interview for {self.application.candidate_name} on {self.scheduled_date}"
    
    @property
    def interview_end_time(self):
        """Calculate interview end time"""
        from datetime import timedelta
        return self.scheduled_date + timedelta(minutes=self.duration)
    
    @property
    def is_upcoming(self):
        """Check if interview is in the future"""
        return self.scheduled_date > timezone.now() and self.status == 'scheduled'


class CandidateTag(models.Model):
    """Tags for categorizing candidates"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="tags")
    tag = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    created_by = models.ForeignKey(Recruiter, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.tag} for {self.application.candidate_name}"

class CandidateCommunication(models.Model):
    """Track all communications with candidate"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="communications")
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE)
    communication_type = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('call', 'Phone Call'),
        ('message', 'Message'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
    ])
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_outgoing = models.BooleanField(default=True)
    attachments = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.communication_type} to {self.application.candidate_name}"