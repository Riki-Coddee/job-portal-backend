# notifications/views.py
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta

from .models import Notification
from .serializers import NotificationSerializer, MarkAsReadSerializer

# Get logger
logger = logging.getLogger('accounts')

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get notifications for current user"""
        user = self.request.user
        logger.debug(f"Notification queryset accessed - User ID: {user.id}")
        
        queryset = Notification.objects.filter(user=user)
        
        # Filter by read status if provided
        read_param = self.request.query_params.get('read')
        if read_param is not None:
            is_read = read_param.lower() == 'true'
            queryset = queryset.filter(is_read=is_read)
            logger.debug(f"Filtering by read status: {is_read}")
        
        # Filter by type if provided
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
            logger.debug(f"Filtering by type: {notification_type}")
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """Get notifications with pagination"""
        user = request.user
        logger.info(f"Notification list accessed - User ID: {user.id}")
        
        queryset = self.filter_queryset(self.get_queryset())
        total_count = queryset.count()
        logger.debug(f"Total notifications found: {total_count}")
        
        # Get limit from query params
        limit = request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
                logger.debug(f"Applying limit: {limit}")
            except ValueError:
                logger.warning(f"Invalid limit parameter: {limit}")
                pass
        
        # Check if we should include stats
        include_stats = request.query_params.get('include_stats', 'false').lower() == 'true'
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            logger.debug(f"Paginated response - Page size: {len(page)}")
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)
            logger.debug(f"Non-paginated response - Count: {len(serializer.data)}")
        
        # Add stats to response if requested
        if include_stats and isinstance(response.data, dict):
            stats = {
                'total': total_count,
                'unread': Notification.objects.filter(user=user, is_read=False).count(),
            }
            response.data['stats'] = stats
            logger.debug(f"Stats included in response - Unread: {stats['unread']}")
        
        logger.info(f"Notifications retrieved successfully - User ID: {user.id}, Count: {total_count}")
        return response
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        user = request.user
        count = Notification.objects.filter(user=user, is_read=False).count()
        logger.info(f"Unread count requested - User ID: {user.id}, Count: {count}")
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """Mark notifications as read"""
        user = request.user
        logger.info(f"Mark notifications as read attempt - User ID: {user.id}")
        
        serializer = MarkAsReadSerializer(data=request.data)
        if serializer.is_valid():
            mark_all = serializer.validated_data.get('mark_all', False)
            notification_ids = serializer.validated_data.get('notification_ids', [])
            
            if mark_all:
                notifications = Notification.objects.filter(
                    user=user,
                    is_read=False
                )
                count = notifications.count()
                for notification in notifications:
                    notification.mark_as_read()
                message = f'Marked all {count} notifications as read'
                logger.info(f"Marked all notifications as read - User ID: {user.id}, Count: {count}")
                
            elif notification_ids:
                notifications = Notification.objects.filter(
                    user=user,
                    id__in=notification_ids,
                    is_read=False
                )
                count = notifications.count()
                for notification in notifications:
                    notification.mark_as_read()
                message = f'Marked {count} notifications as read'
                logger.info(f"Marked specific notifications as read - User ID: {user.id}, Count: {count}, IDs: {notification_ids}")
                
            else:
                logger.warning(f"Invalid mark as read request - User ID: {user.id}, No parameters provided")
                return Response(
                    {'error': 'Provide either mark_all=true or notification_ids'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            unread_count = Notification.objects.filter(user=user, is_read=False).count()
            return Response({
                'status': 'success',
                'message': message,
                'unread_count': unread_count
            })
        
        logger.warning(f"Invalid mark as read data - User ID: {user.id}, Errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Clear all read notifications"""
        user = request.user
        logger.info(f"Clear all read notifications attempt - User ID: {user.id}")
        
        deleted_count, _ = Notification.objects.filter(
            user=user,
            is_read=True
        ).delete()
        
        logger.info(f"Cleared read notifications - User ID: {user.id}, Count: {deleted_count}")
        return Response({
            'status': 'success',
            'message': f'Cleared {deleted_count} read notifications'
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark single notification as read"""
        user = request.user
        notification_id = pk
        logger.info(f"Mark single notification as read - User ID: {user.id}, Notification ID: {notification_id}")
        
        try:
            notification = self.get_object()
            notification.mark_as_read()
            logger.info(f"Notification marked as read - User ID: {user.id}, Notification ID: {notification_id}")
            return Response({'status': 'success', 'message': 'Notification marked as read'})
        except Exception as e:
            logger.error(f"Error marking notification as read - User ID: {user.id}, Notification ID: {notification_id}, Error: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats(request):
    """Get notification statistics"""
    user = request.user
    logger.info(f"Notification stats requested - User ID: {user.id}")
    
    try:
        today = timezone.now().date()
        
        # Calculate stats
        total = Notification.objects.filter(user=user).count()
        unread = Notification.objects.filter(user=user, is_read=False).count()
        today_count = Notification.objects.filter(user=user, created_at__date=today).count()
        
        # Group by type
        by_type = Notification.objects.filter(user=user).values(
            'notification_type'
        ).annotate(count=Count('id')).order_by('-count')
        
        # Recent notifications (last 5)
        recent = Notification.objects.filter(user=user).order_by('-created_at')[:5]
        recent_serializer = NotificationSerializer(recent, many=True)
        
        stats = {
            'total': total,
            'unread': unread,
            'today': today_count,
            'by_type': list(by_type),
            'recent_notifications': recent_serializer.data
        }
        
        logger.info(f"Notification stats retrieved - User ID: {user.id}, Total: {total}, Unread: {unread}")
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Error getting notification stats - User ID: {user.id}, Error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_notification(request):
    """Create a test notification (for development)"""
    user = request.user
    logger.info(f"Test notification creation - User ID: {user.id}")
    
    try:
        from .models import Notification
        
        notification = Notification.objects.create(
            user=user,
            notification_type='system_alert',
            title='Test Notification',
            message='This is a test notification to check if the system is working.',
            priority='medium'
        )
        
        serializer = NotificationSerializer(notification)
        logger.info(f"Test notification created successfully - User ID: {user.id}, Notification ID: {notification.id}")
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error creating test notification - User ID: {user.id}, Error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)