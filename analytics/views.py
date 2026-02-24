# dashboard/views.py
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services import RecruiterDashboardService, AnalyticsService
from accounts.models import Recruiter

# Get logger
logger = logging.getLogger('accounts')  # Using accounts logger or you can create a separate dashboard logger

class RecruiterDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        logger.info(f"Dashboard accessed - User ID: {user.id}, Email: {user.email}")
        
        try:
            recruiter = Recruiter.objects.get(user=user)
            logger.debug(f"Recruiter found - ID: {recruiter.id}, Company: {recruiter.company.name if recruiter.company else 'No Company'}")
            
            service = RecruiterDashboardService(recruiter)
            
            data = {
                'stats': service.get_dashboard_stats(),
                'recent_activities': service.get_recent_activities(),
                'top_performing_jobs': service.get_top_performing_jobs(),
            }
            
            logger.info(f"Dashboard data retrieved successfully for recruiter {recruiter.id}")
            return Response(data, status=status.HTTP_200_OK)
            
        except Recruiter.DoesNotExist:
            logger.warning(f"Non-recruiter user {user.id} attempted to access recruiter dashboard")
            return Response(
                {'error': 'User is not a recruiter'},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error in dashboard for user {user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'An internal error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        time_range = request.GET.get('time_range', 'month')
        logger.info(f"Analytics accessed - User ID: {user.id}, Time Range: {time_range}")
        
        try:
            recruiter = Recruiter.objects.get(user=user)
            logger.debug(f"Recruiter found - ID: {recruiter.id}")
            
            service = AnalyticsService(recruiter)
            
            data = service.get_analytics_overview(time_range)
            
            logger.info(f"Analytics data retrieved successfully for recruiter {recruiter.id}")
            return Response(data, status=status.HTTP_200_OK)
            
        except Recruiter.DoesNotExist:
            logger.warning(f"Non-recruiter user {user.id} attempted to access analytics")
            return Response(
                {'error': 'User is not a recruiter'},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error in analytics for user {user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'An internal error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class QuickStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        logger.info(f"Quick stats accessed - User ID: {user.id}")
        
        try:
            recruiter = Recruiter.objects.get(user=user)
            logger.debug(f"Recruiter found - ID: {recruiter.id}")
            
            service = RecruiterDashboardService(recruiter)
            
            stats = service.get_dashboard_stats()
            
            # Format for quick stats display
            quick_stats = [
                {
                    'title': 'Total Applications',
                    'value': stats['total_applications']['value'],
                    'change': stats['total_applications']['change'],
                    'trend': stats['total_applications']['trend']
                },
                {
                    'title': 'Active Jobs',
                    'value': stats['active_jobs']['value'],
                    'change': stats['active_jobs']['change'],
                    'trend': stats['active_jobs']['trend']
                },
                {
                    'title': 'Interviews Today',
                    'value': service._get_interviews_today(),
                    'change': 'Today',
                    'trend': 'neutral'
                },
                {
                    'title': 'Unread Messages',
                    'value': stats['unread_messages']['value'],
                    'change': stats['unread_messages']['change'],
                    'trend': stats['unread_messages']['trend']
                }
            ]
            
            logger.info(f"Quick stats retrieved successfully for recruiter {recruiter.id}")
            return Response(quick_stats, status=status.HTTP_200_OK)
            
        except Recruiter.DoesNotExist:
            logger.warning(f"Non-recruiter user {user.id} attempted to access quick stats")
            return Response(
                {'error': 'User is not a recruiter'},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error in quick stats for user {user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'An internal error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )