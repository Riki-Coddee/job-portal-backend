# jobs/views.py
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Job, Department
from .serializers import JobSerializer, FeaturedJobSerializer, DepartmentSerializer

# Get logger
logger = logging.getLogger('accounts')

class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        user = self.request.user
        current_time = timezone.now()
        
        # For job seekers (public users)
        if not hasattr(user, 'recruiter'):
            queryset = Job.objects.filter(
                is_active=True,
                is_published=True,
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=current_time)
            ).filter(
                Q(scheduled_date__isnull=True) | Q(scheduled_date__lte=current_time)
            )
            logger.debug(f"Public jobs list accessed - Count: {queryset.count()}")
            return queryset
        
        # For recruiters - show all their jobs (including drafts and scheduled)
        if hasattr(user, 'recruiter'):
            queryset = Job.objects.filter(recruiter=user.recruiter)
            logger.debug(f"Recruiter jobs list accessed - User ID: {user.id}, Count: {queryset.count()}")
            return queryset
        
        logger.warning(f"Unknown user type accessing jobs - User ID: {user.id if user.is_authenticated else 'Anonymous'}")
        return Job.objects.none()
    
    def list(self, request, *args, **kwargs):
        logger.info(f"Jobs list requested - User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        job_id = kwargs.get('pk')
        logger.info(f"Job detail accessed - Job ID: {job_id}, User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        return super().retrieve(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        logger.info(f"Job creation attempt - User ID: {request.user.id}")
        
        if not hasattr(request.user, 'recruiter'):
            logger.warning(f"Non-recruiter user {request.user.id} attempted to create job")
            raise serializers.ValidationError("Only recruiters can post jobs.")
        
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(f"Job created successfully - User ID: {request.user.id}, Job ID: {response.data.get('id')}")
            return response
        except Exception as e:
            logger.error(f"Job creation failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
            raise
    
    def update(self, request, *args, **kwargs):
        job_id = kwargs.get('pk')
        logger.info(f"Job update attempt - User ID: {request.user.id}, Job ID: {job_id}")
        try:
            response = super().update(request, *args, **kwargs)
            logger.info(f"Job updated successfully - User ID: {request.user.id}, Job ID: {job_id}")
            return response
        except Exception as e:
            logger.error(f"Job update failed - User ID: {request.user.id}, Job ID: {job_id}, Error: {str(e)}", exc_info=True)
            raise
    
    def destroy(self, request, *args, **kwargs):
        job_id = kwargs.get('pk')
        logger.info(f"Job deletion attempt - User ID: {request.user.id}, Job ID: {job_id}")
        try:
            response = super().destroy(request, *args, **kwargs)
            logger.info(f"Job deleted successfully - User ID: {request.user.id}, Job ID: {job_id}")
            return response
        except Exception as e:
            logger.error(f"Job deletion failed - User ID: {request.user.id}, Job ID: {job_id}, Error: {str(e)}", exc_info=True)
            raise
    
    def perform_create(self, serializer):
        # Automatically associate job with recruiter
        if hasattr(self.request.user, 'recruiter'):
            serializer.save(recruiter=self.request.user.recruiter)
            logger.debug(f"Job associated with recruiter - User ID: {self.request.user.id}")
        else:
            logger.warning(f"Non-recruiter attempted to create job - User ID: {self.request.user.id}")
            raise serializers.ValidationError("Only recruiters can post jobs.")
    
    @action(detail=True, methods=['post'])
    def publish_now(self, request, pk=None):
        job_id = pk
        logger.info(f"Job publish now attempt - User ID: {request.user.id}, Job ID: {job_id}")
        job = self.get_object()
        job.publish_option = 'immediate'
        job.scheduled_date = timezone.now()
        job.save()
        logger.info(f"Job published successfully - User ID: {request.user.id}, Job ID: {job_id}")
        return Response({'status': 'Job published successfully'})
    
    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        job_id = pk
        logger.info(f"Job schedule attempt - User ID: {request.user.id}, Job ID: {job_id}")
        job = self.get_object()
        scheduled_date = request.data.get('scheduled_date')
        
        if not scheduled_date:
            logger.warning(f"Job schedule missing date - User ID: {request.user.id}, Job ID: {job_id}")
            return Response(
                {'error': 'Scheduled date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job.publish_option = 'schedule'
        job.scheduled_date = scheduled_date
        job.save()
        
        logger.info(f"Job scheduled successfully - User ID: {request.user.id}, Job ID: {job_id}, Date: {scheduled_date}")
        return Response({'status': 'Job scheduled successfully'})
    
    @action(detail=True, methods=['post'])
    def toggle_featured(self, request, pk=None):
        job_id = pk
        logger.info(f"Job featured toggle attempt - User ID: {request.user.id}, Job ID: {job_id}")
        job = self.get_object()
        previous_status = job.is_featured
        job.is_featured = not job.is_featured
        job.save()
        logger.info(f"Job featured toggled - User ID: {request.user.id}, Job ID: {job_id}, New status: {job.is_featured}")
        return Response({'status': 'Featured status updated', 'is_featured': job.is_featured})
    
    @action(detail=False, methods=['get'])
    def scheduled_jobs(self, request):
        user = request.user
        logger.info(f"Scheduled jobs requested - User ID: {user.id if user.is_authenticated else 'Anonymous'}")
        jobs = self.get_queryset().filter(
            publish_option='schedule',
            scheduled_date__gt=timezone.now()
        )
        serializer = self.get_serializer(jobs, many=True)
        logger.info(f"Scheduled jobs retrieved - Count: {jobs.count()}")
        return Response(serializer.data)

    # Add similar jobs action to JobViewSet
    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        job_id = pk
        logger.info(f"Similar jobs requested - Job ID: {job_id}, User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        
        try:
            current_job = self.get_object()
            
            # Get similar jobs based on criteria
            similar_jobs = Job.objects.filter(
                is_active=True,
                is_published=True,
                department=current_job.department
            ).exclude(id=current_job.id).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).filter(
                Q(scheduled_date__isnull=True) | Q(scheduled_date__lte=timezone.now())
            )[:6]  # Limit to 6 similar jobs
            
            # If not enough from same department, expand search
            if similar_jobs.count() < 3:
                similar_jobs = Job.objects.filter(
                    is_active=True,
                    is_published=True,
                    job_type=current_job.job_type
                ).exclude(id=current_job.id).filter(
                    Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
                ).filter(
                    Q(scheduled_date__isnull=True) | Q(scheduled_date__lte=timezone.now())
                )[:6]
            
            serializer = JobSerializer(similar_jobs, many=True, context={'request': request})
            logger.info(f"Similar jobs retrieved - Job ID: {job_id}, Count: {similar_jobs.count()}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting similar jobs - Job ID: {job_id}, Error: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)

# Add a separate API view for homepage featured jobs
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def featured_jobs_homepage(request):
    """
    API endpoint for homepage featured jobs
    """
    count = request.query_params.get('count', 3)
    try:
        count = int(count)
    except ValueError:
        count = 3
    
    logger.info(f"Featured jobs homepage requested - Count: {count}")
    
    current_time = timezone.now()
    
    featured_jobs = Job.objects.filter(
        is_active=True,
        is_published=True,
        is_featured=True,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=current_time)
    ).filter(
        Q(scheduled_date__isnull=True) | Q(scheduled_date__lte=current_time)
    ).order_by('?')[:count]
    
    serializer = JobSerializer(featured_jobs, many=True)
    logger.info(f"Featured jobs retrieved - Count: {featured_jobs.count()}")
    return Response(serializer.data)

# Add the standalone similar jobs API view
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_similar_jobs(request, job_id):
    """Get similar jobs based on job ID"""
    logger.info(f"Similar jobs API called - Job ID: {job_id}")
    
    try:
        current_job = Job.objects.get(id=job_id, is_active=True)
        logger.debug(f"Current job found - Job ID: {job_id}, Title: {current_job.title}")
    except Job.DoesNotExist:
        logger.warning(f"Similar jobs requested for non-existent job - Job ID: {job_id}")
        return Response(
            {'error': 'Job not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get similar jobs based on criteria
    similar_jobs = Job.objects.filter(
        is_active=True,
        is_published=True,
        department=current_job.department
    ).exclude(id=current_job.id).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).filter(
        Q(scheduled_date__isnull=True) | Q(scheduled_date__lte=timezone.now())
    )[:6]  # Limit to 6 similar jobs
    
    # If not enough from same department, expand search
    if similar_jobs.count() < 3:
        similar_jobs = Job.objects.filter(
            is_active=True,
            is_published=True,
            job_type=current_job.job_type
        ).exclude(id=current_job.id).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).filter(
            Q(scheduled_date__isnull=True) | Q(scheduled_date__lte=timezone.now())
        )[:6]
    
    serializer = JobSerializer(similar_jobs, many=True, context={'request': request})
    logger.info(f"Similar jobs retrieved - Job ID: {job_id}, Count: {similar_jobs.count()}")
    return Response(serializer.data)


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Simple read-only viewset for departments"""
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.AllowAny]  # Anyone can view departments
    ordering = ['name']
    
    def list(self, request, *args, **kwargs):
        logger.info(f"Departments list requested - User: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        dept_id = kwargs.get('pk')
        logger.info(f"Department detail accessed - Department ID: {dept_id}")
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def jobs(self, request, pk=None):
        """Get active, published jobs in this department"""
        dept_id = pk
        logger.info(f"Department jobs requested - Department ID: {dept_id}")
        
        department = self.get_object()
        current_time = timezone.now()
        
        jobs = department.jobs.filter(
            is_active=True,
            is_published=True,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=current_time)
        ).filter(
            Q(scheduled_date__isnull=True) | Q(scheduled_date__lte=current_time)
        )
        
        serializer = JobSerializer(jobs, many=True, context={'request': request})
        logger.info(f"Department jobs retrieved - Department ID: {dept_id}, Count: {jobs.count()}")
        return Response(serializer.data)