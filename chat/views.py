# chat/views.py
import logging
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Conversation, Message, TypingIndicator
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    MessageSerializer, CreateMessageSerializer
)

# Get logger
logger = logging.getLogger('accounts')

User = get_user_model()

# Conversation ViewSet with logging
class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Conversation list accessed - User ID: {user.id}")
        
        if hasattr(user, 'recruiter'):
            queryset = Conversation.objects.filter(recruiter=user.recruiter)
            logger.debug(f"User is recruiter - Conversations count: {queryset.count()}")
        elif hasattr(user, 'seeker_profile'):
            queryset = Conversation.objects.filter(job_seeker=user.seeker_profile)
            logger.debug(f"User is job seeker - Conversations count: {queryset.count()}")
        else:
            queryset = Conversation.objects.none()
            logger.warning(f"User {user.id} has no recruiter or seeker profile")
        
        # Handle archived filter
        archived_param = self.request.query_params.get('archived')
        if archived_param is not None:
            archived = archived_param.lower() == 'true'
            queryset = queryset.filter(is_archived=archived)
            logger.debug(f"Filtering archived: {archived}")
        else:
            # Default: show non-archived
            queryset = queryset.filter(is_archived=False)
        
        return queryset.select_related(
            'recruiter__user',
            'job_seeker__user',
            'job',
            'application'
        ).order_by('-last_message_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        logger.info(f"Conversation detail accessed - User ID: {request.user.id}, Conversation ID: {kwargs.get('pk')}")
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a conversation"""
        logger.info(f"Conversation archive attempt - User ID: {request.user.id}, Conversation ID: {pk}")
        conversation = self.get_object()
        conversation.is_archived = True
        conversation.save()
        logger.info(f"Conversation archived successfully - User ID: {request.user.id}, Conversation ID: {pk}")
        return Response({'status': 'success', 'is_archived': True})
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore an archived conversation"""
        logger.info(f"Conversation restore attempt - User ID: {request.user.id}, Conversation ID: {pk}")
        conversation = self.get_object()
        conversation.is_archived = False
        conversation.save()
        logger.info(f"Conversation restored successfully - User ID: {request.user.id}, Conversation ID: {pk}")
        return Response({'status': 'success', 'is_archived': False})
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get all archived conversations"""
        user = request.user
        logger.info(f"Archived conversations accessed - User ID: {user.id}")
        
        if hasattr(user, 'recruiter'):
            queryset = Conversation.objects.filter(recruiter=user.recruiter, is_archived=True)
        elif hasattr(user, 'seeker_profile'):
            queryset = Conversation.objects.filter(job_seeker=user.seeker_profile, is_archived=True)
        else:
            queryset = Conversation.objects.none()
        
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Archived conversations retrieved - User ID: {user.id}, Count: {queryset.count()}")
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark all messages in conversation as read for current user"""
        logger.info(f"Mark read attempt - User ID: {request.user.id}, Conversation ID: {pk}")
        
        try:
            conversation = self.get_object()
            user = request.user
            
            # Verify user has access
            if hasattr(user, 'recruiter') and user.recruiter != conversation.recruiter:
                logger.warning(f"Unauthorized mark read attempt - User ID: {user.id}, Conversation ID: {pk}")
                return Response(
                    {'error': 'You do not have permission'},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif hasattr(user, 'seeker_profile') and user.seeker_profile != conversation.job_seeker:
                logger.warning(f"Unauthorized mark read attempt - User ID: {user.id}, Conversation ID: {pk}")
                return Response(
                    {'error': 'You do not have permission'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get unread messages for this user in this conversation
            unread_messages = Message.objects.filter(
                conversation=conversation,
                receiver=user,
                status__in=['sent', 'delivered']
            )
            
            unread_count = unread_messages.count()
            logger.debug(f"Unread messages found: {unread_count}")
            
            # Update messages to read
            updated_count = 0
            read_time = timezone.now()
            for message in unread_messages:
                message.status = 'read'
                message.read_at = read_time
                message.save(update_fields=['status', 'read_at', 'updated_at'])
                updated_count += 1
            
            # Reset unread count in conversation
            if hasattr(user, 'recruiter') and user.recruiter == conversation.recruiter:
                conversation.unread_by_recruiter = 0
            elif hasattr(user, 'seeker_profile') and user.seeker_profile == conversation.job_seeker:
                conversation.unread_by_job_seeker = 0
            
            conversation.save(update_fields=[
                'unread_by_recruiter', 
                'unread_by_job_seeker', 
                'updated_at'
            ])
            
            logger.info(f"Mark read successful - User ID: {user.id}, Conversation ID: {pk}, Messages marked: {updated_count}")
            return Response({
                'status': 'success',
                'message': f'{updated_count} messages marked as read',
                'unread_count': 0,
                'conversation_id': conversation.id,
                'read_at': read_time.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in mark_read - User ID: {request.user.id}, Conversation ID: {pk}, Error: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get total unread count"""
        user = request.user
        logger.debug(f"Unread count requested - User ID: {user.id}")
        
        if hasattr(user, 'recruiter'):
            conversations = Conversation.objects.filter(recruiter=user.recruiter)
            unread_count = sum(conv.unread_by_recruiter for conv in conversations)
        elif hasattr(user, 'seeker_profile'):
            conversations = Conversation.objects.filter(job_seeker=user.seeker_profile)
            unread_count = sum(conv.unread_by_job_seeker for conv in conversations)
        else:
            unread_count = 0
        
        logger.debug(f"Unread count retrieved - User ID: {user.id}, Count: {unread_count}")
        return Response({'unread_count': unread_count})

# Message ViewSet with logging
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        user = self.request.user
        logger.debug(f"Messages list accessed - User ID: {user.id}, Conversation ID: {conversation_id}")
        
        if not conversation_id:
            return Message.objects.none()
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if user not in [conversation.recruiter.user, conversation.job_seeker.user]:
            logger.warning(f"Unauthorized message access attempt - User ID: {user.id}, Conversation ID: {conversation_id}")
            return Message.objects.none()
        
        return Message.objects.filter(conversation=conversation).order_by('created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMessageSerializer
        return MessageSerializer
    
    def create(self, request, *args, **kwargs):
        conversation_id = self.kwargs.get('conversation_pk')
        user = request.user
        logger.info(f"Message creation attempt - User ID: {user.id}, Conversation ID: {conversation_id}")
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if user not in [conversation.recruiter.user, conversation.job_seeker.user]:
            logger.warning(f"Unauthorized message creation attempt - User ID: {user.id}, Conversation ID: {conversation_id}")
            return Response({"error": "Not part of this conversation"}, status=403)
        
        serializer = CreateMessageSerializer(data=request.data, context={
            'request': request,
            'conversation': conversation
        })
        
        if serializer.is_valid():
            message = serializer.save()
            response_serializer = MessageSerializer(message, context={'request': request})
            logger.info(f"Message created successfully - User ID: {user.id}, Message ID: {message.id}")
            return Response(response_serializer.data, status=201)
        
        logger.warning(f"Message creation validation failed - User ID: {user.id}, Errors: {serializer.errors}")
        return Response(serializer.errors, status=400)
    
    def retrieve(self, request, *args, **kwargs):
        logger.debug(f"Message detail accessed - User ID: {request.user.id}, Message ID: {kwargs.get('pk')}")
        return super().retrieve(request, *args, **kwargs)

# Typing Indicator View with logging
class TypingIndicatorView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, conversation_id):
        user = request.user
        logger.debug(f"Typing indicator update - User ID: {user.id}, Conversation ID: {conversation_id}, is_typing: {request.data.get('is_typing')}")
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if request.user not in [conversation.recruiter.user, conversation.job_seeker.user]:
            logger.warning(f"Unauthorized typing indicator attempt - User ID: {user.id}, Conversation ID: {conversation_id}")
            return Response({"error": "Not part of this conversation"}, status=403)
        
        is_typing = request.data.get('is_typing', False)
        
        typing_indicator, created = TypingIndicator.objects.get_or_create(
            conversation=conversation,
            user=request.user
        )
        typing_indicator.is_typing = is_typing
        typing_indicator.save()
        
        logger.debug(f"Typing indicator updated - User ID: {user.id}, is_typing: {is_typing}")
        return Response({'status': 'typing indicator updated'})

# Online Status Views with logging
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_online_status(request, user_id):
    """Get online status and last activity for a user"""
    logger.info(f"Online status requested - Requesting User ID: {request.user.id}, Target User ID: {user_id}")
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get online status using the model method
        is_online = user.get_online_status() if hasattr(user, 'get_online_status') else False
        
        # If user is marked online but not actually online, update the database
        if hasattr(user, 'is_online') and user.is_online and not is_online:
            user.is_online = False
            user.save(update_fields=['is_online'])
            logger.debug(f"User {user_id} online status corrected to offline")
        
        # Format last activity for display
        last_activity_display = None
        if hasattr(user, 'last_activity') and user.last_activity:
            now = timezone.now()
            diff = now - user.last_activity
            seconds = diff.total_seconds()
            
            if seconds < 60:
                last_activity_display = "Just now"
            elif seconds < 3600:  # < 1 hour
                minutes = int(seconds / 60)
                last_activity_display = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif seconds < 86400:  # < 24 hours
                hours = int(seconds / 3600)
                last_activity_display = f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif seconds < 604800:  # < 7 days
                days = int(seconds / 86400)
                last_activity_display = f"{days} day{'s' if days != 1 else ''} ago"
            else:
                last_activity_display = user.last_activity.strftime('%b %d, %Y')
        
        response_data = {
            'is_online': is_online,
            'last_activity': user.last_activity.isoformat() if hasattr(user, 'last_activity') and user.last_activity else None,
            'last_activity_display': last_activity_display,
            'status': 'online' if is_online else 'offline'
        }
        
        logger.info(f"Online status retrieved - User ID: {user_id}, is_online: {is_online}")
        return Response(response_data)
        
    except User.DoesNotExist:
        logger.warning(f"Online status requested for non-existent user - User ID: {user_id}")
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting online status - User ID: {user_id}, Error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_users_online_status(request):
    """Get online status for multiple users at once"""
    user_ids = request.data.get('user_ids', [])
    logger.info(f"Batch online status requested - User ID: {request.user.id}, User IDs count: {len(user_ids)}")
    
    if not user_ids:
        logger.debug("No user IDs provided for batch status")
        return Response({})
    
    users = User.objects.filter(id__in=user_ids)
    status_data = {}
    
    for user in users:
        is_online = user.get_online_status() if hasattr(user, 'get_online_status') else False
        
        # Update if needed
        if hasattr(user, 'is_online') and user.is_online and not is_online:
            user.is_online = False
            user.save(update_fields=['is_online'])
            logger.debug(f"User {user.id} online status corrected to offline")
        
        # Format last activity
        last_activity_display = None
        if hasattr(user, 'last_activity') and user.last_activity:
            now = timezone.now()
            diff = now - user.last_activity
            seconds = diff.total_seconds()
            
            if seconds < 60:
                last_activity_display = "Just now"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                last_activity_display = f"{minutes}m ago"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                last_activity_display = f"{hours}h ago"
            else:
                days = int(seconds / 86400)
                last_activity_display = f"{days}d ago"
        
        status_data[str(user.id)] = {
            'is_online': is_online,
            'last_activity': user.last_activity.isoformat() if hasattr(user, 'last_activity') and user.last_activity else None,
            'last_activity_display': last_activity_display
        }
    
    logger.info(f"Batch online status retrieved - User ID: {request.user.id}, Success count: {len(status_data)}")
    return Response(status_data)