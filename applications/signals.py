# applications/signals.py (create this file)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Application
from chat.models import Conversation, Message

# applications/signals.py - Update the signal
@receiver(post_save, sender=Application)
def create_conversation_on_application(sender, instance, created, **kwargs):
    """
    Automatically create a conversation when a new application is submitted
    """
    if created:
        try:
            # Check if conversation already exists between this recruiter and job_seeker
            conversation = Conversation.objects.filter(
                recruiter=instance.job.recruiter,
                job_seeker=instance.seeker
            ).first()
            
            if not conversation:
                # Create conversation only if it doesn't exist
                conversation = Conversation.objects.create(
                    application=instance,
                    job=instance.job,
                    recruiter=instance.job.recruiter,
                    job_seeker=instance.seeker,
                    subject=f"Regarding your application for {instance.job.title}",
                    last_message_at=timezone.now()
                )
                
                # Create welcome message from recruiter
                Message.objects.create(
                    conversation=conversation,
                    sender=instance.job.recruiter.user,
                    receiver=instance.seeker.user,
                    content=f"Hello {instance.seeker.user.first_name}! Thank you for applying for the {instance.job.title} position. This chat is for communication regarding your application.",
                    message_type='system',
                    is_system_message=True,
                    status='sent'
                )
                
                # Optional: Add a snippet from cover letter
                if instance.cover_letter:
                    Message.objects.create(
                        conversation=conversation,
                        sender=instance.seeker.user,
                        receiver=instance.job.recruiter.user,
                        content=f"Application cover letter: {instance.cover_letter[:300]}...",
                        message_type='text',
                        status='sent'
                    )
            else:
                # Update existing conversation with current application reference
                conversation.application = instance
                conversation.job = instance.job
                conversation.save()
                
        except Exception as e:
            # Log error but don't break the application creation
            print(f"Error creating/updating conversation for application {instance.id}: {e}")