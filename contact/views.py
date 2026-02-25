import logging
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import FAQ, ContactMessage
from .serializers import FAQSerializer, ContactMessageSerializer, ContactMessageDetailSerializer

logger = logging.getLogger(__name__)


class FAQListView(generics.ListAPIView):
    """Public list of active FAQs"""
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]


class ContactMessageCreateView(APIView):
    """Submit a contact message with email notifications"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        
        if serializer.is_valid():
            # Save the message with additional data
            message = serializer.save(
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Send email notifications
            try:
                self.send_notification_emails(message)
            except Exception as e:
                logger.error(f"Failed to send email notifications: {e}")
                # Don't fail the request if email fails
                pass
            
            return Response({
                'success': True,
                'message': 'Your message has been sent successfully. We\'ll respond within 24 hours.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def send_notification_emails(self, message):
        """Send both admin notification and user confirmation emails"""
        
        # Get SITE_URL from settings with a fallback
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        # 1. Send email to admin
        admin_context = {
            'name': message.name,
            'email': message.email,
            'category': message.get_category_display(),
            'subject': message.subject,
            'message': message.message,
            'created_at': message.created_at,
            'ip_address': message.ip_address,
            'admin_url': f"{site_url}/admin/contact/contactmessage/{message.id}/change/"
        }
        
        admin_html = render_to_string('contact/email/admin_notification.html', admin_context)
        admin_text = strip_tags(admin_html)
        
        send_mail(
            subject=f"New Contact Message: {message.subject}",
            message=admin_text,
            html_message=admin_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        
        # 2. Send confirmation email to user
        user_context = {
            'name': message.name,
            'category': message.get_category_display(),
            'subject': message.subject,
            'message': message.message,
            'year': message.created_at.year,
            'site_url': site_url,
        }
        
        user_html = render_to_string('contact/email/user_confirmation.html', user_context)
        user_text = strip_tags(user_html)
        
        send_mail(
            subject=f"We received your message - {message.subject}",
            message=user_text,
            html_message=user_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[message.email],
            fail_silently=False,
        )