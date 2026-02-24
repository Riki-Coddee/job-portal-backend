# chat/models.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import Recruiter, JobSeeker, CustomUser
from applications.models import Application
from jobs.models import Job
import os

class Conversation(models.Model):
    """
    A conversation between a recruiter and a job seeker
    Usually linked to a specific job application
    """
    application = models.ForeignKey(
        Application, 
        on_delete=models.CASCADE, 
        related_name='conversations',
        null=True, 
        blank=True,
        help_text="Linked application (optional)"
    )
    job = models.ForeignKey(
        Job, 
        on_delete=models.CASCADE, 
        related_name='conversations',
        null=True,
        blank=True
    )
    recruiter = models.ForeignKey(
        Recruiter, 
        on_delete=models.CASCADE, 
        related_name='conversations'
    )
    job_seeker = models.ForeignKey(
        JobSeeker, 
        on_delete=models.CASCADE, 
        related_name='conversations'
    )
    
    # Conversation details
    subject = models.CharField(max_length=255, blank=True)
    is_archived = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Unread counts
    unread_by_recruiter = models.PositiveIntegerField(default=0)
    unread_by_job_seeker = models.PositiveIntegerField(default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-last_message_at', '-updated_at']
        unique_together = ['recruiter', 'job_seeker']
        indexes = [
            models.Index(fields=['recruiter', 'updated_at']),
            models.Index(fields=['job_seeker', 'updated_at']),
            models.Index(fields=['application']),
        ]
    
    def __str__(self):
        return f"Chat: {self.recruiter} ↔ {self.job_seeker}"
    
    def get_other_participant(self, user=None):
        """Get the other participant in the conversation"""
        if not user:
            return None
        
        try:
            if user == self.recruiter.user:
                return self.job_seeker
            elif user == self.job_seeker.user:
                return self.recruiter
        except AttributeError:
            # Handle cases where relationships might not be loaded
            pass
        
        return None
            
    def mark_as_read(self, user):
        """Mark conversation as read for a specific user"""
        if user == self.recruiter.user:
            self.unread_by_recruiter = 0
        elif user == self.job_seeker.user:
            self.unread_by_job_seeker = 0
        self.save()
    
    def increment_unread(self, recipient_user):
        """Increment unread count for recipient only"""
        if not recipient_user:
            return
        
        # Make sure we're not incrementing for the sender
        # Get the last message to check sender
        last_message = self.messages.order_by('-created_at').first()
        if last_message and last_message.sender == recipient_user:
            # This is the sender's own message, don't increment
            return
        
        # Only increment for the receiver
        if recipient_user == self.recruiter.user:
            self.unread_by_recruiter = models.F('unread_by_recruiter') + 1
        elif recipient_user == self.job_seeker.user:
            self.unread_by_job_seeker = models.F('unread_by_job_seeker') + 1
        
        # Use update_fields to avoid race conditions
        self.save(update_fields=['unread_by_recruiter', 'unread_by_job_seeker', 'updated_at'])
        
    def get_unread_count(self, user):
        """Get unread count for a specific user"""
        if user == self.recruiter.user:
            return self.unread_by_recruiter
        elif user == self.job_seeker.user:
            return self.unread_by_job_seeker
        return 0

    
class Message(models.Model):
    """
    Individual message in a conversation
    """
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='received_messages'
    )
    
    # Message content
    content = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('interview', 'Interview Invitation'),
            ('offer', 'Job Offer'),
            ('document', 'Document'),
            ('system', 'System Message'),
        ],
        default='text'
    )
    
    # Message status
    status = models.CharField(
        max_length=20,
        choices=[
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('read', 'Read'),
            ('failed', 'Failed'),
        ],
        default='sent'
    )
    
    # Attachments
    # attachments = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # System messages
    is_system_message = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['receiver', 'created_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.email[:20]}..."
    
    def mark_as_read(self):
        """Mark message as read - PROPER FIX"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.status = 'read'  # Make sure status is updated too
            self.save(update_fields=['read_at', 'status', 'updated_at'])
            
    # Remove or fix the save method override if it's causing issues
    def save(self, *args, **kwargs):
        # Don't automatically update conversation's last_message_at here
        # Only do it for new messages, not for updates
        if not self.pk:  # This is a new message
            if self.conversation:
                self.conversation.last_message_at = self.created_at or timezone.now()
                self.conversation.save()
        super().save(*args, **kwargs)

        
    def update_conversation_unread_count(self):
        """Update conversation unread count after message is read"""
        conversation = self.conversation
        receiver = self.receiver
        
        # Only update if this was the last unread message
        # We can check if there are any other unread messages for this user
        unread_count = conversation.messages.filter(
            receiver=receiver,
            read_at__isnull=True
        ).count()
        
        if receiver == conversation.recruiter.user:
            conversation.unread_by_recruiter = unread_count
        elif receiver == conversation.job_seeker.user:
            conversation.unread_by_job_seeker = unread_count
        
        conversation.save(update_fields=['unread_by_recruiter', 'unread_by_job_seeker', 'updated_at'])

class MessageAttachment(models.Model):
    """
    File attachments for messages
    """
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='attachments'  # Changed from 'message_attachments'
    )
    file = models.FileField(upload_to='chat_attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Add these methods for better file handling
    def clean(self):
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if self.file_size > max_size:
            raise ValidationError(f'File size cannot exceed 10MB. Current size: {self.file_size}')
        
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.txt', '.zip', '.rar']
        ext = os.path.splitext(self.file_name)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(f'File type {ext} is not allowed. Allowed types: {", ".join(allowed_extensions)}')
    
    def get_file_url(self):
        """Get file URL"""
        if self.file:
            return self.file.url
        return None
    
    def is_image(self):
        """Check if file is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        ext = os.path.splitext(self.file_name)[1].lower()
        return ext in image_extensions
    
    def __str__(self):
        return self.file_name

class ConversationSettings(models.Model):
    """
    User-specific settings for conversations
    """
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='chat_settings'
    )
    # Notification settings
    message_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    sound_notifications = models.BooleanField(default=True)
    
    # Privacy settings
    allow_typing_indicator = models.BooleanField(default=True)
    allow_read_receipts = models.BooleanField(default=True)
    allow_file_sharing = models.BooleanField(default=True)
    max_file_size_mb = models.PositiveIntegerField(default=10)
    allowed_file_types = models.JSONField(default=list, blank=True)
    
    # Auto-reply settings
    auto_reply_enabled = models.BooleanField(default=False)
    auto_reply_message = models.TextField(blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Chat settings for {self.user.email}"

class TypingIndicator(models.Model):
    """
    Track when users are typing
    """
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='typing_indicators'
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_typing = models.BooleanField(default=False)
    last_typing_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['conversation', 'user']
    
    def __str__(self):
        return f"{self.user.email} typing in {self.conversation}"
