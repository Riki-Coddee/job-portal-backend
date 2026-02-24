# chat/serializers.py - FIXED VERSION
from rest_framework import serializers
from django.utils import timezone
import mimetypes
from .models import Conversation, Message, MessageAttachment
from accounts.serializers import UserBasicSerializer

# Add this import at the top if not present
import os

class MessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file_name', 'file_size', 'file_type', 'file_url', 'thumbnail_url', 'uploaded_at', 'is_image']
        read_only_fields = ['uploaded_at']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_thumbnail_url(self, obj):
        """Generate thumbnail URL for images"""
        if obj.is_image():
            request = self.context.get('request')
            if request and obj.file:
                return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_is_image(self, obj):
        return obj.is_image()

class MessageSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)
    receiver = UserBasicSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    is_own_message = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'receiver', 'content', 
            'message_type', 'status', 'attachments', 'created_at',
            'read_at', 'is_system_message', 'is_own_message', 'formatted_time'
        ]
        read_only_fields = ['created_at', 'updated_at', 'read_at']
    
    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and obj.sender:
            return request.user == obj.sender
        return False
    
    def get_formatted_time(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%I:%M %p')
        return ''
    
    def get_attachments(self, obj):
        """Fetch attachments for the message"""
        # First, try to get attachments through the related manager
        try:
            # Try with the correct related_name
            attachments_qs = obj.attachments.all()
        except AttributeError:
            try:
                # Try with old related_name
                attachments_qs = obj.message_attachments.all()
            except AttributeError:
                # Fallback to direct query
                attachments_qs = MessageAttachment.objects.filter(message=obj)
        
        if attachments_qs.exists():
            serializer = MessageAttachmentSerializer(
                attachments_qs, 
                many=True, 
                context=self.context
            )
            return serializer.data
        return []

class CreateMessageSerializer(serializers.ModelSerializer):
    attachments = serializers.ListField(
        child=serializers.FileField(
            max_length=10000000,  # 10MB
            allow_empty_file=True,
            use_url=False,
            required=False
        ),
        required=False,
        write_only=True,
        allow_empty=True
    )
    
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'attachments']
        extra_kwargs = {
            'content': {'required': False, 'allow_blank': True},
            'message_type': {'required': False, 'default': 'text'}
        }
    
    def validate(self, attrs):
        """Custom validation to ensure either content or attachments are present"""
        content = attrs.get('content', '').strip()
        attachments = attrs.get('attachments', [])
        
        if not content and not attachments:
            raise serializers.ValidationError({
                'non_field_errors': ['Either content or attachments must be provided.']
            })
        
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        conversation = self.context.get('conversation')
        
        if not conversation:
            raise serializers.ValidationError({"conversation": "Conversation not found"})
        
        if request.user == conversation.recruiter.user:
            sender_type = 'recruiter'
            receiver = conversation.job_seeker.user
        else:
            sender_type = 'job_seeker'
            receiver = conversation.recruiter.user
        
        # Extract attachments from validated data
        attachments = validated_data.pop('attachments', [])
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            receiver=receiver,
            content=validated_data.get('content', ''),
            message_type=validated_data.get('message_type', 'text'),
            status='sent'
        )
        
        # Save attachments if any
        for attachment in attachments:
            # Get file type
            content_type = getattr(attachment, 'content_type', None)
            if not content_type:
                # Try to guess from filename
                content_type = mimetypes.guess_type(attachment.name)[0] or 'application/octet-stream'
            
            MessageAttachment.objects.create(
                message=message,
                file=attachment,
                file_name=attachment.name,
                file_size=attachment.size,
                file_type=content_type
            )
        
        # Update conversation
        conversation.last_message_at = timezone.now()
        conversation.save()
        
        # Update unread count for the receiver
        if hasattr(conversation, 'increment_unread'):
            conversation.increment_unread(receiver)
        
        return message

# chat/serializers.py - Updated ConversationListSerializer
class ConversationListSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'subject', 'last_message_at', 'is_archived', 'is_pinned',
            'unread_by_recruiter', 'unread_by_job_seeker', 'other_participant',
            'unread_count', 'last_message', 'created_at',
            'recruiter', 'job_seeker', 'job', 'application'
        ]
        read_only_fields = ['created_at']
    
    def get_other_participant(self, obj):
        """Get other participant info with online status"""
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user:
            return None
        
        try:
            # Determine which participant is the current user
            if hasattr(user, 'recruiter') and user.recruiter == obj.recruiter:
                # Current user is the recruiter, other is job seeker
                other = obj.job_seeker
                other_user = other.user
                participant_type = 'job_seeker'
                
                # Get online status
                is_online = other_user.get_online_status()
                
                result = {
                    'id': other.id,
                    'user_id': other_user.id,
                    'name': f"{other_user.first_name} {other_user.last_name}",
                    'email': other_user.email,
                    'type': participant_type,
                    'is_online': is_online,
                    'last_activity': other_user.last_activity.isoformat() if other_user.last_activity else None
                }
                
                # Add job seeker specific fields
                if other.title:
                    result['title'] = other.title
                
                # Try to add skills if available
                try:
                    if hasattr(other, 'skills') and hasattr(other.skills, 'all'):
                        skills = other.skills.all()
                        if hasattr(skills, 'values_list'):
                            result['skills'] = list(skills.values_list('name', flat=True))[:3]
                except:
                    result['skills'] = []
                
            elif hasattr(user, 'seeker_profile') and user.seeker_profile == obj.job_seeker:
                # Current user is the job seeker, other is recruiter
                other = obj.recruiter
                other_user = other.user
                participant_type = 'recruiter'
                
                # Get online status
                is_online = other_user.get_online_status()
                
                result = {
                    'id': other.id,
                    'user_id': other_user.id,
                    'name': f"{other_user.first_name} {other_user.last_name}",
                    'email': other_user.email,
                    'type': participant_type,
                    'is_online': is_online,
                    'last_activity': other_user.last_activity.isoformat() if other_user.last_activity else None
                }
                
                # Add company info if available
                if hasattr(other, 'company') and other.company:
                    result['company'] = other.company.name
                    result['company_id'] = other.company.id
                    if hasattr(other.company, 'logo') and other.company.logo:
                        result['company_logo'] = other.company.logo.url if other.company.logo else None
            else:
                return None
            
            return result
            
        except Exception as e:
            print(f"Error in get_other_participant: {e}")
            return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return 0
        
        try:
            # Get unread count for the current user
            return obj.get_unread_count(request.user)
        except Exception as e:
            # Fallback to model field
            if request.user == obj.recruiter.user:
                return obj.unread_by_recruiter
            elif request.user == obj.job_seeker.user:
                return obj.unread_by_job_seeker
            return 0
    
    def get_last_message(self, obj):
        try:
            last_message = obj.messages.order_by('-created_at').first()
            if last_message:
                return {
                    'id': last_message.id,
                    'content': last_message.content[:100] if last_message.content else '',
                    'sender_id': last_message.sender.id,
                    'created_at': last_message.created_at,
                    'status': last_message.status,
                    'is_own_message': last_message.sender == self.context['request'].user if self.context.get('request') else False
                }
        except Exception as e:
            print(f"Error getting last message: {e}")
        return None

class ConversationDetailSerializer(ConversationListSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + ['messages']
