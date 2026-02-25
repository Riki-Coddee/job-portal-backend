from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import json

User = get_user_model()

class UserSettings(models.Model):
    """User preferences and settings"""
    
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System Default'),
    ]
    
    DENSITY_CHOICES = [
        ('comfortable', 'Comfortable'),
        ('cozy', 'Cozy'),
        ('compact', 'Compact'),
    ]
    
    FONT_SIZE_CHOICES = [
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    ]
    
    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('spanish', 'Spanish'),
        ('french', 'French'),
        ('german', 'German'),
        ('japanese', 'Japanese'),
    ]
    
    TIMEZONE_CHOICES = [
        ('America/Los_Angeles', 'Pacific Time (PT)'),
        ('America/Denver', 'Mountain Time (MT)'),
        ('America/Chicago', 'Central Time (CT)'),
        ('America/New_York', 'Eastern Time (ET)'),
        ('Europe/London', 'London (GMT)'),
        ('Asia/Tokyo', 'Tokyo (JST)'),
    ]
    
    DATE_FORMAT_CHOICES = [
        ('MM/DD/YYYY', 'MM/DD/YYYY'),
        ('DD/MM/YYYY', 'DD/MM/YYYY'),
        ('YYYY-MM-DD', 'YYYY-MM-DD'),
    ]
    
    EMAIL_DIGEST_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('never', 'Never'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    
    # General settings
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='english')
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='America/Los_Angeles')
    date_format = models.CharField(max_length=20, choices=DATE_FORMAT_CHOICES, default='MM/DD/YYYY')
    auto_save = models.BooleanField(default=True)
    email_digest = models.CharField(max_length=10, choices=EMAIL_DIGEST_CHOICES, default='weekly')
    
    # Appearance settings
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    density = models.CharField(max_length=15, choices=DENSITY_CHOICES, default='comfortable')
    font_size = models.CharField(max_length=10, choices=FONT_SIZE_CHOICES, default='medium')
    compact_mode = models.BooleanField(default=False)
    
    # Notification settings (stored as JSON)
    email_notifications = models.JSONField(default=dict)
    push_notifications = models.JSONField(default=dict)
    in_app_notifications = models.JSONField(default=dict)
    
    # Security settings
    two_factor_enabled = models.BooleanField(default=False)
    login_alerts = models.BooleanField(default=True)
    session_timeout = models.IntegerField(default=30, validators=[MinValueValidator(5), MaxValueValidator(120)])
    ip_whitelist_enabled = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Settings'
        verbose_name_plural = 'User Settings'
    
    def __str__(self):
        return f"Settings for {self.user.email}"
    
    def save(self, *args, **kwargs):
        # Set default notification settings if not provided
        if not self.email_notifications:
            self.email_notifications = {
                'newApplications': True,
                'interviewUpdates': True,
                'messages': True,
                'jobExpiry': False,
                'weeklySummary': True,
                'marketingEmails': False,
            }
        if not self.push_notifications:
            self.push_notifications = {
                'newApplications': True,
                'interviewReminders': True,
                'messages': True,
                'mentions': True,
            }
        if not self.in_app_notifications:
            self.in_app_notifications = {
                'all': True,
                'sound': True,
            }
        super().save(*args, **kwargs)


class TeamMember(models.Model):
    """Team members for company accounts"""
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('recruiter', 'Recruiter'),
        ('viewer', 'Viewer'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('inactive', 'Inactive'),
    ]
    
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='team_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invites')
    invited_email = models.EmailField()
    invited_at = models.DateTimeField(auto_now_add=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['company', 'user']
    
    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.role})"


class TeamInvite(models.Model):
    """Pending team invitations"""
    
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='pending_invites')
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=TeamMember.ROLE_CHOICES, default='viewer')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Invite for {self.email} to {self.company.name}"