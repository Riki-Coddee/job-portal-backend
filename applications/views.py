# applications/views.py
import logging
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.db.models import Q, Count, Avg, F
from chat.models import Conversation
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Application, ApplicationNote, Interview, CandidateTag, CandidateCommunication
from .serializers import (
    ApplicationSerializer, ApplicationNoteSerializer,
    InterviewSerializer, CandidateTagSerializer,
    CandidateCommunicationSerializer, ApplicationUpdateSerializer, JobSeekerApplicationSerializer
)
from accounts.models import Recruiter, JobSeeker
from jobs.models import Job
import json
import math
from datetime import timedelta

# Get logger
logger = logging.getLogger('accounts')

# applications/views.py - Updated ApplicationViewSet with logging
class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    parser_classes = (MultiPartParser, FormParser)
    
    search_fields = [
        'seeker__user__first_name', 'seeker__user__last_name',
        'seeker__user__email', 'job__title'
    ]
    ordering_fields = ['applied_at', 'match_score', 'last_active']
    ordering = ['-applied_at']
    
    def get_queryset(self):
        """Get applications for current recruiter's jobs"""
        user = self.request.user
        logger.debug(f"Application list accessed - User ID: {user.id}")
        
        # Get recruiter profile
        recruiter = get_object_or_404(Recruiter, user=user)
        
        # Get applications for jobs posted by this recruiter
        queryset = Application.objects.filter(
            job__recruiter=recruiter
        ).select_related(
            'seeker__user', 
            'job'
        )
        
        # Apply filters
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            logger.debug(f"Filtering by status: {status_filter}")
            queryset = queryset.filter(status=status_filter)
        
        favorite_filter = self.request.query_params.get('is_favorite', None)
        if favorite_filter:
            if favorite_filter.lower() == 'true':
                queryset = queryset.filter(is_favorite=True)
            elif favorite_filter.lower() == 'false':
                queryset = queryset.filter(is_favorite=False)
        
        archived_filter = self.request.query_params.get('is_archived', None)
        if archived_filter:
            if archived_filter.lower() == 'true':
                queryset = queryset.filter(is_archived=True)
            elif archived_filter.lower() == 'false':
                queryset = queryset.filter(is_archived=False)
        
        job_filter = self.request.query_params.get('job', None)
        if job_filter:
            logger.debug(f"Filtering by job ID: {job_filter}")
            queryset = queryset.filter(job_id=job_filter)
        
        return queryset

# applications/views.py - JobSeekerApplicationViewSet with logging
class JobSeekerApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for job seekers to manage their own applications"""
    serializer_class = JobSeekerApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        """Get applications for current job seeker with proper filtering"""
        user = self.request.user
        logger.debug(f"Job seeker applications accessed - User ID: {user.id}")
        
        if hasattr(user, 'seeker_profile'):
            queryset = Application.objects.filter(
                seeker=user.seeker_profile
            ).select_related(
                'job',
                'job__recruiter__user'
            ).prefetch_related(
                'tags',
                'notes',
                'interviews'
            )
            
            # Apply filters from query parameters
            status_filter = self.request.query_params.get('status')
            if status_filter:
                logger.debug(f"Filtering by status: {status_filter}")
                queryset = queryset.filter(status=status_filter)
            
            # Search functionality if needed
            search = self.request.query_params.get('search')
            if search:
                logger.debug(f"Searching applications with term: {search}")
                queryset = queryset.filter(
                    Q(job__title__icontains=search) |
                    Q(job__company__icontains=search)
                )
            
            # Ordering
            ordering = self.request.query_params.get('ordering', '-applied_at')
            if ordering in ['applied_at', '-applied_at', 'match_score', '-match_score']:
                queryset = queryset.order_by(ordering)
            
            return queryset
        return Application.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Override list to include stats as expected by React frontend"""
        logger.info(f"Job seeker applications list - User ID: {request.user.id}")
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get pagination if needed
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)
        
        # Add stats to response
        if hasattr(request.user, 'seeker_profile'):
            stats = self.calculate_application_stats(queryset)
            # Add stats to response data
            if isinstance(response.data, dict):
                response.data['stats'] = stats
            elif isinstance(response.data, list):
                response.data = {
                    'results': response.data,
                    'stats': stats
                }
            
            logger.info(f"Job seeker applications retrieved - User ID: {request.user.id}, Total: {stats['total']}")
        
        return response
    
    def calculate_application_stats(self, applications):
        """Calculate statistics for applications"""
        total = applications.count()
        
        # Calculate status breakdown
        status_breakdown = {}
        for app in applications:
            status = app.status
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        # Calculate average score
        scored_applications = applications.filter(match_score__gt=0)
        if scored_applications.exists():
            average_score = scored_applications.aggregate(
                avg_score=Avg('match_score')
            )['avg_score']
            average_score = math.ceil(average_score)  # Round up to nearest integer
        else:
            average_score = 0
        
        return {
            'total': total,
            'statusBreakdown': status_breakdown,
            'averageScore': average_score
        }
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get detailed dashboard statistics for job seeker"""
        logger.info(f"Job seeker dashboard stats requested - User ID: {request.user.id}")
        
        if not hasattr(request.user, 'seeker_profile'):
            logger.warning(f"Non-job-seeker user {request.user.id} attempted to access dashboard stats")
            return Response({'error': 'Not a job seeker'}, status=403)
        
        applications = self.get_queryset()
        total = applications.count()
        
        # Status breakdown
        status_counts = applications.values('status').annotate(
            count=Count('id')
        )
        status_breakdown = {
            item['status']: item['count'] 
            for item in status_counts
        }
        
        # Recent applications (last 30 days)
        recent_applications = applications.filter(
            applied_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Average match score
        avg_score = applications.aggregate(
            avg=Avg('match_score')
        )['avg'] or 0
        
        # Interviews scheduled
        interviews_scheduled = Interview.objects.filter(
            application__in=applications,
            status='scheduled'
        ).count()
        
        response_data = {
            'total_applications': total,
            'recent_applications': recent_applications,
            'average_match_score': round(avg_score, 1),
            'status_breakdown': status_breakdown,
            'interviews_scheduled': interviews_scheduled,
            'offers_received': applications.filter(status='offer').count(),
            'applications_today': applications.filter(
                applied_at__date=timezone.now().date()
            ).count()
        }
        
        logger.info(f"Dashboard stats retrieved - User ID: {request.user.id}, Total: {total}")
        return Response(response_data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get single application with all details"""
        logger.info(f"Application detail accessed - User ID: {request.user.id}, Application ID: {kwargs.get('pk')}")
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update application - used for withdrawing applications"""
        logger.info(f"Application update attempt - User ID: {request.user.id}, Application ID: {kwargs.get('pk')}")
        instance = self.get_object()
        
        # Check if this is a withdrawal request
        if request.data.get('action') == 'withdraw':
            instance.status = 'withdrawn'
            instance.save()
            logger.info(f"Application withdrawn - User ID: {request.user.id}, Application ID: {kwargs.get('pk')}")
            return Response({'status': 'Application withdrawn successfully'})
        
        # Otherwise use normal update
        try:
            response = super().update(request, *args, **kwargs)
            logger.info(f"Application updated successfully - User ID: {request.user.id}, Application ID: {kwargs.get('pk')}")
            return response
        except Exception as e:
            logger.error(f"Application update failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
            raise
    
    def destroy(self, request, *args, **kwargs):
        """Withdraw/delete application with file cleanup"""
        logger.info(f"Application deletion attempt - User ID: {request.user.id}, Application ID: {kwargs.get('pk')}")
        instance = self.get_object()
        
        # Store the file path before deletion
        file_path = None
        if instance.resume_snapshot:
            file_path = instance.resume_snapshot.path if hasattr(instance.resume_snapshot, 'path') else instance.resume_snapshot.name
        
        # Delete the instance
        instance.delete()
        logger.info(f"Application deleted successfully - User ID: {request.user.id}, Application ID: {kwargs.get('pk')}")
        
        # Optional: Manual cleanup if needed
        if file_path:
            try:
                from django.core.files.storage import default_storage
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                    logger.debug(f"Resume file deleted: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete resume file: {str(e)}")
        
        return Response(status=204)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw application (alternative to DELETE)"""
        logger.info(f"Application withdrawal via action - User ID: {request.user.id}, Application ID: {pk}")
        instance = self.get_object()
        instance.status = 'withdrawn'
        instance.save()
        logger.info(f"Application withdrawn successfully via action - User ID: {request.user.id}, Application ID: {pk}")
        return Response({'status': 'Application withdrawn successfully'})
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update application status"""
        logger.info(f"Application status update - User ID: {request.user.id}, Application ID: {pk}")
        instance = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Application.STATUS_CHOICES):
            logger.warning(f"Invalid status update attempt - User ID: {request.user.id}, Status: {new_status}")
            return Response(
                {'error': 'Invalid status'},
                status=400
            )
        
        instance.status = new_status
        instance.save()
        logger.info(f"Application status updated to {new_status} - User ID: {request.user.id}, Application ID: {pk}")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new application"""
        logger.info(f"Application creation attempt - User ID: {request.user.id}")
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(f"Application created successfully - User ID: {request.user.id}")
            return response
        except serializers.ValidationError as e:
            logger.warning(f"Application creation validation error - User ID: {request.user.id}, Error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Application creation failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to create application: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# apply_to_job function with logging
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def apply_to_job(request, job_id):
    """API endpoint for job seekers to apply to a job with skill ratings"""
    logger.info(f"Job application attempt - User ID: {request.user.id}, Job ID: {job_id}")
    
    # Check if user has seeker_profile
    if not hasattr(request.user, 'seeker_profile'):
        logger.warning(f"Non-job-seeker user {request.user.id} attempted to apply to job")
        return Response(
            {'error': 'Only job seekers can apply for jobs'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        job = Job.objects.get(id=job_id, is_active=True)
        logger.debug(f"Job found - Job ID: {job_id}, Title: {job.title}")
    except Job.DoesNotExist:
        logger.warning(f"Job not found or not active - Job ID: {job_id}")
        return Response(
            {'error': 'Job not found or not active'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if already applied
    existing_application = Application.objects.filter(
        job=job,
        seeker=request.user.seeker_profile
    ).first()
    
    if existing_application:
        logger.warning(f"Duplicate application attempt - User ID: {request.user.id}, Job ID: {job_id}")
        return Response(
            {'error': 'You have already applied for this job'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get application data
    cover_letter = request.data.get('cover_letter', '')
    use_profile_resume = request.data.get('use_profile_resume', 'true').lower() == 'true'
    custom_resume = request.FILES.get('resume')
    profile_resume_only = request.data.get('profile_resume_only', 'false').lower() == 'true'
    
    # Get skills data from frontend
    skills_data = request.data.get('skills')
    try:
        if skills_data:
            skills = json.loads(skills_data) if isinstance(skills_data, str) else skills_data
        else:
            skills = []
    except json.JSONDecodeError:
        logger.warning(f"Invalid skills data format - User ID: {request.user.id}")
        return Response(
            {'error': 'Invalid skills data format'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get additional info
    additional_info_data = request.data.get('additional_info')
    try:
        if additional_info_data:
            additional_info = json.loads(additional_info_data) if isinstance(additional_info_data, str) else additional_info_data
        else:
            additional_info = {}
    except json.JSONDecodeError:
        additional_info = {}
    
    # Get match score
    match_score = request.data.get('match_score', 50)
    try:
        match_score = int(match_score)
        if match_score < 0 or match_score > 100:
            match_score = 50
    except (ValueError, TypeError):
        match_score = 50
    
    # Validate required fields
    if not cover_letter:
        logger.warning(f"Missing cover letter - User ID: {request.user.id}")
        return Response(
            {'error': 'Cover letter is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not use_profile_resume and not custom_resume:
        logger.warning(f"Missing resume - User ID: {request.user.id}")
        return Response(
            {'error': 'Please upload a resume or use your profile resume'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate match score from skills if not provided
    if not match_score and skills:
        total_rating = 0
        max_rating = 0
        for skill in skills:
            rating = skill.get('rating', 0)
            if rating > 0:
                total_rating += rating
                max_rating += 5
        
        if max_rating > 0:
            match_score = int((total_rating / max_rating) * 100)
        else:
            match_score = 50
    
    # Create application
    try:
        with transaction.atomic():
            application = Application.objects.create(
                job=job,
                seeker=request.user.seeker_profile,
                cover_letter=cover_letter,
                skills=skills,
                additional_info=additional_info,
                match_score=match_score,
                status='new',
                last_active=timezone.now()
            )
            logger.debug(f"Application record created - ID: {application.id}")
            
            # Handle resume
            if use_profile_resume:
                if request.user.seeker_profile.resume:
                    # Copy the profile resume to application resume
                    from django.core.files.base import ContentFile
                    import os
                    
                    profile_resume = request.user.seeker_profile.resume
                    if profile_resume and hasattr(profile_resume, 'file'):
                        # Get the file content
                        file_content = profile_resume.file.read()
                        
                        # Create a new file for the application
                        file_name = os.path.basename(profile_resume.name)
                        application.resume_snapshot.save(
                            file_name,
                            ContentFile(file_content),
                            save=True
                        )
                        logger.debug(f"Profile resume copied to application - User ID: {request.user.id}")
                elif custom_resume:
                    # Fallback to custom resume if profile resume doesn't exist
                    application.resume_snapshot = custom_resume
                    logger.debug(f"Custom resume used as fallback - User ID: {request.user.id}")
            elif custom_resume:
                # Use custom resume
                application.resume_snapshot = custom_resume
                logger.debug(f"Custom resume uploaded - User ID: {request.user.id}")
            
            application.save()
            
            # Handle conversation
            recruiter = job.recruiter
            job_seeker = request.user.seeker_profile
            
            # Check if a conversation already exists
            conversation = Conversation.objects.filter(
                recruiter=recruiter,
                job_seeker=job_seeker
            ).first()
            
            # If no conversation exists, create one
            if not conversation:
                conversation = Conversation.objects.create(
                    application=application,
                    job=job,
                    recruiter=recruiter,
                    job_seeker=job_seeker,
                    subject=f"Chat with {job_seeker.user.get_full_name()}",
                    last_message_at=timezone.now()
                )
                logger.info(f"New conversation created - ID: {conversation.id}, User ID: {request.user.id}")
                
                # Create welcome messages
                from chat.models import Message
                
                # Welcome message from recruiter
                Message.objects.create(
                    conversation=conversation,
                    sender=recruiter.user,
                    receiver=job_seeker.user,
                    content=f"Hello {job_seeker.user.first_name}! Thank you for applying for the {job.title} position. This chat is for communication regarding your application.",
                    message_type='system',
                    is_system_message=True,
                    status='sent'
                )
                
                # Optional: Add cover letter as a message if not too long
                if len(cover_letter) > 0 and len(cover_letter) < 1000:
                    Message.objects.create(
                        conversation=conversation,
                        sender=job_seeker.user,
                        receiver=recruiter.user,
                        content=f"Cover Letter:\n\n{cover_letter}",
                        message_type='text',
                        status='sent'
                    )
                elif len(cover_letter) >= 1000:
                    Message.objects.create(
                        conversation=conversation,
                        sender=job_seeker.user,
                        receiver=recruiter.user,
                        content=f"Cover Letter (truncated):\n\n{cover_letter[:500]}...",
                        message_type='text',
                        status='sent'
                    )
            
            # Serialize response
            serializer = ApplicationSerializer(application, context={'request': request})
            
            response_data = {
                'success': True,
                'message': 'Application submitted successfully',
                'application': serializer.data,
                'match_score': match_score,
                'skills_count': len(skills),
                'resume_uploaded': bool(application.resume_snapshot),
                'conversation_exists': conversation is not None
            }
            
            if conversation:
                from chat.serializers import ConversationListSerializer
                conv_serializer = ConversationListSerializer(
                    conversation, 
                    context={'request': request}
                )
                response_data['conversation'] = conv_serializer.data
            
            logger.info(f"Application submitted successfully - User ID: {request.user.id}, Application ID: {application.id}")
            return Response(response_data, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"Application submission failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
        import traceback
        print(f"Error in apply_to_job: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {'error': f'Failed to submit application: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# InterviewViewSet with logging
class InterviewViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Interview list accessed - User ID: {user.id}")
        
        # Check if user is a job seeker
        if hasattr(user, 'seeker_profile'):
            # Job seeker can see their own interviews
            return Interview.objects.filter(
                application__seeker=user.seeker_profile
            ).select_related(
                'application', 
                'application__job',
                'scheduled_by__user'
            )
        # Recruiter can see interviews for their applications
        elif hasattr(user, 'recruiter'):
            recruiter = user.recruiter
            return Interview.objects.filter(
                application__job__recruiter=recruiter
            ).select_related(
                'application', 
                'application__seeker__user',
                'scheduled_by__user'
            )
        return Interview.objects.none()
    
    def create(self, request, *args, **kwargs):
        logger.info(f"Interview creation attempt - User ID: {request.user.id}")
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(f"Interview created successfully - User ID: {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Interview creation failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark interview as completed (recruiter only)"""
        logger.info(f"Interview completion attempt - User ID: {request.user.id}, Interview ID: {pk}")
        
        if not hasattr(request.user, 'recruiter'):
            logger.warning(f"Non-recruiter user {request.user.id} attempted to complete interview")
            return Response({'error': 'Recruiters only'}, status=403)
        
        interview = self.get_object()
        feedback = request.data.get('feedback', '')
        rating = request.data.get('rating')
        
        interview.status = 'completed'
        interview.feedback = feedback
        if rating:
            interview.rating = rating
        interview.save()
        
        logger.info(f"Interview marked as completed - Interview ID: {pk}, User ID: {request.user.id}")
        return Response({'status': 'Interview marked as completed'})

class CandidateTagViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Candidate tag list accessed - User ID: {user.id}")
        recruiter = get_object_or_404(Recruiter, user=user)
        return CandidateTag.objects.filter(
            application__job__recruiter=recruiter
        ).select_related(
            'application', 
            'created_by'
        )
    
    def perform_create(self, serializer):
        user = self.request.user
        logger.info(f"Candidate tag creation attempt - User ID: {user.id}")
        recruiter = get_object_or_404(Recruiter, user=user)
        serializer.save(created_by=recruiter)
        logger.info(f"Candidate tag created successfully - User ID: {user.id}")

class CandidateCommunicationViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateCommunicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Candidate communication list accessed - User ID: {user.id}")
        recruiter = get_object_or_404(Recruiter, user=user)
        return CandidateCommunication.objects.filter(
            application__job__recruiter=recruiter
        ).select_related(
            'application', 
            'recruiter'
        )
    
    def perform_create(self, serializer):
        user = self.request.user
        logger.info(f"Candidate communication creation attempt - User ID: {user.id}")
        recruiter = get_object_or_404(Recruiter, user=user)
        serializer.save(recruiter=recruiter)
        logger.info(f"Candidate communication created successfully - User ID: {user.id}")

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sync_chat_conversations(request):
    """
    Sync all applications to conversations for the current user
    Creates conversations for applications that don't have them yet
    """
    from chat.models import Conversation, Message
    
    user = request.user
    logger.info(f"Conversation sync requested - User ID: {user.id}")
    
    try:
        if hasattr(user, 'seeker_profile'):
            # User is a job seeker
            job_seeker = user.seeker_profile
            applications = Application.objects.filter(seeker=job_seeker)
            
            created_conversations = []
            
            for application in applications:
                # Check if conversation exists for this application
                conversation = Conversation.objects.filter(
                    application=application,
                    job=application.job,
                    recruiter=application.job.recruiter,
                    job_seeker=job_seeker
                ).first()
                
                if not conversation:
                    # Create conversation
                    conversation = Conversation.objects.create(
                        application=application,
                        job=application.job,
                        recruiter=application.job.recruiter,
                        job_seeker=job_seeker,
                        subject=f"Regarding your application for {application.job.title}",
                        last_message_at=timezone.now()
                    )
                    
                    # Create a welcome message
                    Message.objects.create(
                        conversation=conversation,
                        sender=application.job.recruiter.user,
                        receiver=job_seeker.user,
                        content=f"Hello {job_seeker.user.first_name}! Thank you for applying for the {application.job.title} position. This chat is for communication regarding your application.",
                        message_type='system',
                        is_system_message=True,
                        status='sent'
                    )
                    
                    created_conversations.append(conversation.id)
                    logger.debug(f"Conversation created for application {application.id}")
            
            logger.info(f"Conversation sync completed for job seeker - User ID: {user.id}, Created: {len(created_conversations)}")
            return Response({
                'message': f'Synced {len(created_conversations)} new conversations',
                'created_conversations': created_conversations,
                'total_applications': applications.count()
            })
            
        elif hasattr(user, 'recruiter'):
            # User is a recruiter
            recruiter = user.recruiter
            applications = Application.objects.filter(job__recruiter=recruiter)
            
            created_conversations = []
            
            for application in applications:
                # Check if conversation exists for this application
                conversation = Conversation.objects.filter(
                    application=application,
                    job=application.job,
                    recruiter=recruiter,
                    job_seeker=application.seeker
                ).first()
                
                if not conversation:
                    # Create conversation
                    conversation = Conversation.objects.create(
                        application=application,
                        job=application.job,
                        recruiter=recruiter,
                        job_seeker=application.seeker,
                        subject=f"Regarding application for {application.job.title}",
                        last_message_at=timezone.now()
                    )
                    
                    # Create a welcome message
                    Message.objects.create(
                        conversation=conversation,
                        sender=recruiter.user,
                        receiver=application.seeker.user,
                        content=f"Hello {application.seeker.user.first_name}! Thank you for applying for the {application.job.title} position. This chat is for communication regarding your application.",
                        message_type='system',
                        is_system_message=True,
                        status='sent'
                    )
                    
                    created_conversations.append(conversation.id)
                    logger.debug(f"Conversation created for application {application.id}")
            
            logger.info(f"Conversation sync completed for recruiter - User ID: {user.id}, Created: {len(created_conversations)}")
            return Response({
                'message': f'Synced {len(created_conversations)} new conversations',
                'created_conversations': created_conversations,
                'total_applications': applications.count()
            })
        
        else:
            logger.warning(f"User {user.id} attempted sync without proper profile")
            return Response(
                {'error': 'User must be either a job seeker or recruiter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Conversation sync failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to sync conversations: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_application_conversations(request, application_id=None):
    """
    Get conversations related to applications
    If application_id is provided, get conversations for that specific application
    Otherwise, get all conversations for user's applications
    """
    from chat.models import Conversation
    from chat.serializers import ConversationListSerializer
    
    user = request.user
    logger.info(f"Application conversations requested - User ID: {user.id}, Application ID: {application_id}")
    
    try:
        if application_id:
            # Get specific application
            application = get_object_or_404(Application, id=application_id)
            
            # Check permissions
            if hasattr(user, 'seeker_profile'):
                if application.seeker != user.seeker_profile:
                    logger.warning(f"Unauthorized application conversation access - User ID: {user.id}, Application ID: {application_id}")
                    return Response(
                        {'error': 'Not authorized to view this application'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif hasattr(user, 'recruiter'):
                if application.job.recruiter != user.recruiter:
                    logger.warning(f"Unauthorized application conversation access - User ID: {user.id}, Application ID: {application_id}")
                    return Response(
                        {'error': 'Not authorized to view this application'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Get conversation for this application
            conversations = Conversation.objects.filter(application=application)
            
        else:
            # Get all conversations for user's applications
            if hasattr(user, 'seeker_profile'):
                conversations = Conversation.objects.filter(job_seeker=user.seeker_profile)
            elif hasattr(user, 'recruiter'):
                conversations = Conversation.objects.filter(recruiter=user.recruiter)
            else:
                logger.warning(f"User {user.id} attempted to get conversations without proper profile")
                return Response(
                    {'error': 'User must be either a job seeker or recruiter'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Filter by application if needed
        has_application = request.query_params.get('has_application', None)
        if has_application is not None:
            if has_application.lower() == 'true':
                conversations = conversations.filter(application__isnull=False)
            elif has_application.lower() == 'false':
                conversations = conversations.filter(application__isnull=True)
        
        serializer = ConversationListSerializer(
            conversations, 
            many=True, 
            context={'request': request}
        )
        
        logger.info(f"Application conversations retrieved - User ID: {user.id}, Count: {conversations.count()}")
        return Response({
            'conversations': serializer.data,
            'count': conversations.count()
        })
        
    except Exception as e:
        logger.error(f"Failed to get application conversations - User ID: {user.id}, Error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to get conversations: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# SIMPLIFIED DASHBOARD ENDPOINTS with logging
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def application_stats(request):
    """Simple stats for recruiter dashboard - /api/applications/stats/"""
    user = request.user
    logger.info(f"Application stats requested - User ID: {user.id}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to access application stats")
        return Response({'error': 'Recruiters only'}, status=403)
    
    recruiter = user.recruiter
    apps = Application.objects.filter(job__recruiter=recruiter)
    
    stats = {
        'total': apps.count(),
        'new_today': apps.filter(applied_at__date=timezone.now().date()).count(),
        'avg_match_score': apps.aggregate(Avg('match_score'))['match_score__avg'] or 0,
        'pending_interviews': Interview.objects.filter(
            application__job__recruiter=recruiter,
            status='scheduled'
        ).count()
    }
    
    logger.info(f"Application stats retrieved - User ID: {user.id}, Total: {stats['total']}")
    return Response(stats)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_status(request, pk):
    """Update application status - /api/applications/{id}/update_status/"""
    user = request.user
    logger.info(f"Application status update via endpoint - User ID: {user.id}, Application ID: {pk}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to update application status")
        return Response({'error': 'Recruiters only'}, status=403)
    
    try:
        app = Application.objects.get(id=pk, job__recruiter=user.recruiter)
    except Application.DoesNotExist:
        logger.warning(f"Application not found - User ID: {user.id}, Application ID: {pk}")
        return Response({'error': 'Not found'}, status=404)
    
    new_status = request.data.get('status')
    if new_status:
        app.status = new_status
        app.save()
        logger.info(f"Application status updated to {new_status} - User ID: {user.id}, Application ID: {pk}")
        return Response({'success': True})
    
    logger.warning(f"Missing status in update request - User ID: {user.id}, Application ID: {pk}")
    return Response({'error': 'Status required'}, status=400)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_favorite(request, pk):
    """Toggle favorite - /api/applications/{id}/toggle_favorite/"""
    user = request.user
    logger.info(f"Toggle favorite attempt - User ID: {user.id}, Application ID: {pk}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to toggle favorite")
        return Response({'error': 'Recruiters only'}, status=403)
    
    try:
        app = Application.objects.get(id=pk, job__recruiter=user.recruiter)
    except Application.DoesNotExist:
        logger.warning(f"Application not found - User ID: {user.id}, Application ID: {pk}")
        return Response({'error': 'Not found'}, status=404)
    
    app.is_favorite = not app.is_favorite
    app.save()
    logger.info(f"Favorite toggled to {app.is_favorite} - User ID: {user.id}, Application ID: {pk}")
    return Response({'is_favorite': app.is_favorite})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_score(request, pk):
    """Update match score - /api/applications/{id}/update_score/"""
    user = request.user
    logger.info(f"Score update attempt - User ID: {user.id}, Application ID: {pk}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to update score")
        return Response({'error': 'Recruiters only'}, status=403)
    
    try:
        app = Application.objects.get(id=pk, job__recruiter=user.recruiter)
    except Application.DoesNotExist:
        logger.warning(f"Application not found - User ID: {user.id}, Application ID: {pk}")
        return Response({'error': 'Not found'}, status=404)
    
    score = request.data.get('score')
    if score is not None:
        try:
            app.match_score = int(score)
            app.save()
            logger.info(f"Score updated to {score} - User ID: {user.id}, Application ID: {pk}")
            return Response({'success': True})
        except ValueError:
            logger.warning(f"Invalid score value: {score} - User ID: {user.id}")
            return Response({'error': 'Invalid score'}, status=400)
    
    logger.warning(f"Missing score in update request - User ID: {user.id}")
    return Response({'error': 'Score required'}, status=400)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def schedule_interview(request, pk):
    """Schedule interview - /api/applications/{id}/schedule_interview/"""
    user = request.user
    logger.info(f"Interview scheduling attempt - User ID: {user.id}, Application ID: {pk}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to schedule interview")
        return Response({'error': 'Recruiters only'}, status=403)
    
    try:
        app = Application.objects.get(id=pk, job__recruiter=user.recruiter)
    except Application.DoesNotExist:
        logger.warning(f"Application not found - User ID: {user.id}, Application ID: {pk}")
        return Response({'error': 'Not found'}, status=404)
    
    data = request.data
    try:
        interview = Interview.objects.create(
            application=app,
            scheduled_date=data.get('scheduled_date'),
            interview_type=data.get('interview_type', 'video'),
            duration=data.get('duration', 60),
            meeting_link=data.get('meeting_link', ''),
            location=data.get('location', ''),
            status='scheduled'
        )
        app.interview_scheduled = data.get('scheduled_date')
        app.status = 'interview'
        app.save()
        logger.info(f"Interview scheduled successfully - Interview ID: {interview.id}, User ID: {user.id}")
        return Response({'success': True})
    except Exception as e:
        logger.error(f"Interview scheduling failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_note(request, pk):
    """Add note - /api/applications/{id}/add_note/"""
    user = request.user
    logger.info(f"Add note attempt - User ID: {user.id}, Application ID: {pk}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to add note")
        return Response({'error': 'Recruiters only'}, status=403)
    
    try:
        app = Application.objects.get(id=pk, job__recruiter=user.recruiter)
    except Application.DoesNotExist:
        logger.warning(f"Application not found - User ID: {user.id}, Application ID: {pk}")
        return Response({'error': 'Not found'}, status=404)
    
    note_text = request.data.get('note')
    if note_text:
        ApplicationNote.objects.create(
            application=app,
            recruiter=user.recruiter,
            note=note_text
        )
        logger.info(f"Note added successfully - User ID: {user.id}, Application ID: {pk}")
        return Response({'success': True})
    
    logger.warning(f"Missing note text - User ID: {user.id}")
    return Response({'error': 'Note required'}, status=400)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_app(request, pk):
    """Delete application - /api/applications/{id}/"""
    user = request.user
    logger.info(f"Application deletion attempt - User ID: {user.id}, Application ID: {pk}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to delete application")
        return Response({'error': 'Recruiters only'}, status=403)
    
    try:
        app = Application.objects.get(id=pk, job__recruiter=user.recruiter)
        app.delete()
        logger.info(f"Application deleted successfully - User ID: {user.id}, Application ID: {pk}")
        return Response({'success': True})
    except Application.DoesNotExist:
        logger.warning(f"Application not found - User ID: {user.id}, Application ID: {pk}")
        return Response({'error': 'Not found'}, status=404)

# Job stats with logging
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def job_stats(request):
    """Simple job stats - /api/jobs/stats/"""
    user = request.user
    logger.info(f"Job stats requested - User ID: {user.id}")
    
    if not hasattr(user, 'recruiter'):
        logger.warning(f"Non-recruiter user {user.id} attempted to access job stats")
        return Response({'error': 'Recruiters only'}, status=403)
    
    jobs = Job.objects.filter(recruiter=user.recruiter)
    apps = Application.objects.filter(job__recruiter=user.recruiter)
    
    stats = {
        'total_jobs': jobs.count(),
        'published_jobs': jobs.filter(is_published=True).count(),
        'total_applications': apps.count()
    }
    
    logger.info(f"Job stats retrieved - User ID: {user.id}, Total Jobs: {stats['total_jobs']}")
    return Response(stats)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def jobseeker_application_stats(request):
    """Get application statistics for job seeker dashboard"""
    user = request.user
    logger.info(f"Job seeker application stats requested - User ID: {user.id}")
    
    if not hasattr(user, 'seeker_profile'):
        logger.warning(f"Non-job-seeker user {user.id} attempted to access application stats")
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    applications = Application.objects.filter(
        seeker=user.seeker_profile
    )
    
    # Calculate stats
    total = applications.count()
    
    # Status breakdown
    status_counts = applications.values('status').annotate(
        count=Count('id')
    )
    status_breakdown = {
        item['status']: item['count'] 
        for item in status_counts
    }
    
    # Average match score (only for scored applications)
    scored_apps = applications.filter(match_score__gt=0)
    if scored_apps.exists():
        avg_score_result = scored_apps.aggregate(
            avg=Avg('match_score')
        )
        average_score = round(avg_score_result['avg'], 1)
    else:
        average_score = 0
    
    # Applications by time period
    today = applications.filter(
        applied_at__date=timezone.now().date()
    ).count()
    
    last_7_days = applications.filter(
        applied_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    last_30_days = applications.filter(
        applied_at__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Pending interviews
    pending_interviews = Interview.objects.filter(
        application__in=applications,
        status='scheduled'
    ).count()
    
    stats = {
        'total': total,
        'statusBreakdown': status_breakdown,
        'averageScore': average_score,
        'periodStats': {
            'today': today,
            'last7Days': last_7_days,
            'last30Days': last_30_days
        },
        'pendingInterviews': pending_interviews,
        'offers': applications.filter(status='offer').count(),
        'rejections': applications.filter(status='rejected').count()
    }
    
    logger.info(f"Job seeker application stats retrieved - User ID: {user.id}, Total: {total}")
    return Response(stats)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_jobseeker_interviews(request):
    """Get all interviews for current job seeker"""
    user = request.user
    logger.info(f"Job seeker interviews requested - User ID: {user.id}")
    
    if not hasattr(user, 'seeker_profile'):
        logger.warning(f"Non-job-seeker user {user.id} attempted to access interviews")
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    interviews = Interview.objects.filter(
        application__seeker=user.seeker_profile
    ).select_related(
        'application',
        'application__job',
        'scheduled_by__user'
    ).order_by('-scheduled_date')
    
    serializer = InterviewSerializer(interviews, many=True, context={'request': request})
    logger.info(f"Job seeker interviews retrieved - User ID: {user.id}, Count: {interviews.count()}")
    return Response(serializer.data)