# accounts/views.py
import logging
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .models import CustomUser, Recruiter, JobSeeker, Skill, Education, Experience
from companies.models import Company
from .serializers import (
    UserRegistrationSerializer, EmailTokenObtainPairSerializer, 
    CurrentRecruiterSerializer, JobSeekerProfileSerializer, 
    JobSeekerUpdateSerializer, ExperienceSerializer, EducationSerializer, 
    SkillSerializer, RecruiterProfileSerializer, RecruiterUpdateSerializer, 
    CompanyUpdateSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser

# Get logger for accounts app
logger = logging.getLogger('accounts')

User = get_user_model()

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        logger.info(f"Login attempt for email: {request.data.get('email', 'unknown')}")
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                logger.info(f"Login successful for email: {request.data.get('email')}")
            else:
                logger.warning(f"Login failed for email: {request.data.get('email')}")
            return response
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            raise

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        logger.info(f"Registration attempt with email: {request.data.get('email', 'unknown')}")
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                logger.info(f"User registered successfully - ID: {user.id}, Email: {user.email}, Role: {user.role}")
                
                response_data = {
                    'message': f'{user.role.replace("_", " ").title()} registered successfully',
                    'user_id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
                
                if user.role == 'recruiter' and hasattr(user, 'recruiter'):
                    response_data['company'] = user.recruiter.company.name if user.recruiter.company else None
                    response_data['designation'] = user.recruiter.designation
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Error during user registration: {str(e)}", exc_info=True)
                return Response({
                    'error': 'Registration failed due to internal error'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Log validation errors
        logger.warning(f"Registration validation failed for email {request.data.get('email')}: {serializer.errors}")
        
        # Return structured errors
        errors = {}
        for field, error_list in serializer.errors.items():
            if isinstance(error_list, list):
                errors[field] = error_list[0] if error_list else "Invalid value"
            else:
                errors[field] = str(error_list)
        
        return Response({
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserView(APIView):
    """Simple endpoint to get current user data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        logger.debug(f"Current user data accessed - User ID: {user.id}, Email: {user.email}")
        
        data = {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        return Response(data)

class CheckEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        logger.info(f"Email check requested for: {email}")
        
        if not email:
            logger.warning("Email check attempted without email parameter")
            return Response({'error': 'Email is required'}, status=400)
        
        try:
            if CustomUser.objects.filter(email=email).exists():
                user = CustomUser.objects.get(email=email)
                logger.info(f"Email exists: {email} (Role: {user.role})")
                return Response({
                    'exists': True,
                    'role': user.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                })
            
            logger.info(f"Email not found: {email}")
            return Response({'exists': False})
        except Exception as e:
            logger.error(f"Error checking email {email}: {str(e)}", exc_info=True)
            return Response({'error': 'Error checking email'}, status=500)

class CurrentRecruiterView(generics.RetrieveAPIView):
    """
    Get current authenticated recruiter's profile
    URL: /api/accounts/recruiter/me/
    Method: GET
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CurrentRecruiterSerializer
    
    def get_object(self):
        user = self.request.user
        logger.debug(f"Recruiter profile accessed - User ID: {user.id}")
        
        if user.role != 'recruiter':
            logger.warning(f"Non-recruiter user {user.id} attempted to access recruiter profile")
            raise PermissionDenied({"error": "User is not a recruiter"})
        
        try:
            return Recruiter.objects.get(user=user)
        except Recruiter.DoesNotExist:
            logger.error(f"Recruiter profile not found for user {user.id}")
            raise NotFound({"error": "Recruiter profile not found. Please complete your profile setup."})

class JobSeekerProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update job seeker profile
    URL: /api/accounts/job-seeker/profile/
    Methods: GET, PATCH
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return JobSeekerProfileSerializer
        return JobSeekerUpdateSerializer
    
    def get_object(self):
        user = self.request.user
        logger.debug(f"Job seeker profile accessed - User ID: {user.id}")
        
        if user.role != 'job_seeker':
            logger.warning(f"Non-job-seeker user {user.id} attempted to access job seeker profile")
            raise PermissionDenied({"error": "User is not a job seeker"})
        
        try:
            return JobSeeker.objects.get(user=user)
        except JobSeeker.DoesNotExist:
            logger.error(f"Job seeker profile not found for user {user.id}")
            raise NotFound({"error": "Job seeker profile not found"})
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Calculate profile completion
        completion_data = self.calculate_profile_completion(instance)
        response_data = serializer.data
        response_data['profile_completion'] = completion_data
        
        logger.info(f"Job seeker profile retrieved - User ID: {request.user.id}, Completion: {completion_data['percentage']}%")
        return Response(response_data)
    
    def update(self, request, *args, **kwargs):
        logger.info(f"Job seeker profile update attempt - User ID: {request.user.id}")
        try:
            response = super().update(request, *args, **kwargs)
            logger.info(f"Job seeker profile updated successfully - User ID: {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Job seeker profile update failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
            raise
    
    def calculate_profile_completion(self, job_seeker):
        """Calculate profile completion percentage"""
        sections = {
            'basic_info': ['title', 'location', 'phone_number', 'bio'],
            'professional': ['experiences'],
            'education': ['educations'],
            'skills': ['skills'],
            'documents': ['resume', 'portfolio_url', 'github_url', 'linkedin_url']
        }
        
        total_points = 0
        earned_points = 0
        
        # Basic Info (25% weight)
        for field in sections['basic_info']:
            total_points += 5
            if field == 'bio':
                if getattr(job_seeker, field) and len(getattr(job_seeker, field)) > 50:
                    earned_points += 5
            elif getattr(job_seeker, field):
                earned_points += 5
        
        # Professional Experience (30% weight)
        total_points += 30
        if job_seeker.experiences.exists():
            earned_points += 30
        
        # Education (20% weight)
        total_points += 20
        if job_seeker.educations.exists():
            earned_points += 20
        
        # Skills (15% weight)
        total_points += 15
        if job_seeker.skills.count() >= 3:
            earned_points += 15
        elif job_seeker.skills.exists():
            earned_points += 10
        
        # Documents/Links (10% weight)
        doc_points = 0
        for field in sections['documents']:
            if getattr(job_seeker, field):
                doc_points += 2.5
        total_points += 10
        earned_points += min(doc_points, 10)
        
        percentage = (earned_points / total_points) * 100 if total_points > 0 else 0
        
        # Get checklist
        checklist = [
            {
                'id': 1,
                'label': 'Complete your bio',
                'completed': bool(job_seeker.bio and len(job_seeker.bio) > 50),
                'weight': 5,
                'field': 'bio'
            },
            {
                'id': 2,
                'label': 'Add your professional title',
                'completed': bool(job_seeker.title),
                'weight': 5,
                'field': 'title'
            },
            {
                'id': 3,
                'label': 'Add location',
                'completed': bool(job_seeker.location),
                'weight': 5,
                'field': 'location'
            },
            {
                'id': 4,
                'label': 'Add phone number',
                'completed': bool(job_seeker.phone_number),
                'weight': 5,
                'field': 'phone_number'
            },
            {
                'id': 5,
                'label': 'Add at least one work experience',
                'completed': job_seeker.experiences.exists(),
                'weight': 30,
                'field': 'experiences'
            },
            {
                'id': 6,
                'label': 'Add education',
                'completed': job_seeker.educations.exists(),
                'weight': 20,
                'field': 'educations'
            },
            {
                'id': 7,
                'label': 'Add at least 3 skills',
                'completed': job_seeker.skills.count() >= 3,
                'weight': 15,
                'field': 'skills'
            },
            {
                'id': 8,
                'label': 'Upload your resume',
                'completed': bool(job_seeker.resume),
                'weight': 2.5,
                'field': 'resume'
            },
            {
                'id': 9,
                'label': 'Add portfolio/GitHub links',
                'completed': bool(job_seeker.portfolio_url or job_seeker.github_url),
                'weight': 7.5,
                'field': 'links'
            }
        ]
        
        return {
            'percentage': round(percentage),
            'checklist': checklist
        }

# Experience Views
class ExperienceListCreateView(generics.ListCreateAPIView):
    """List and create experiences for job seeker"""
    permission_classes = [IsAuthenticated]
    serializer_class = ExperienceSerializer
    
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Experience list accessed - User ID: {user.id}")
        
        if user.role != 'job_seeker':
            logger.warning(f"Non-job-seeker user {user.id} attempted to access experiences")
            raise PermissionDenied({"error": "User is not a job seeker"})
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            return Experience.objects.filter(job_seeker=job_seeker)
        except JobSeeker.DoesNotExist:
            logger.error(f"Job seeker profile not found for user {user.id}")
            raise NotFound({"error": "Job seeker profile not found"})
    
    def perform_create(self, serializer):
        user = self.request.user
        logger.info(f"Experience creation attempt - User ID: {user.id}")
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            serializer.save(job_seeker=job_seeker)
            logger.info(f"Experience created successfully - User ID: {user.id}")
        except JobSeeker.DoesNotExist:
            logger.error(f"Job seeker profile not found for user {user.id}")
            raise NotFound({"error": "Job seeker profile not found"})
        except Exception as e:
            logger.error(f"Experience creation failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise

class ExperienceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete an experience"""
    permission_classes = [IsAuthenticated]
    serializer_class = ExperienceSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role != 'job_seeker':
            raise PermissionDenied({"error": "User is not a job seeker"})
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            return Experience.objects.filter(job_seeker=job_seeker)
        except JobSeeker.DoesNotExist:
            raise NotFound({"error": "Job seeker profile not found"})
    
    def perform_update(self, serializer):
        user = self.request.user
        logger.info(f"Experience update attempt - User ID: {user.id}, Experience ID: {self.kwargs.get('pk')}")
        try:
            serializer.save()
            logger.info(f"Experience updated successfully - User ID: {user.id}")
        except Exception as e:
            logger.error(f"Experience update failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise
    
    def perform_destroy(self, instance):
        user = self.request.user
        logger.info(f"Experience deletion attempt - User ID: {user.id}, Experience ID: {instance.id}")
        try:
            instance.delete()
            logger.info(f"Experience deleted successfully - User ID: {user.id}")
        except Exception as e:
            logger.error(f"Experience deletion failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise

# Education Views
class EducationListCreateView(generics.ListCreateAPIView):
    """List and create educations for job seeker"""
    permission_classes = [IsAuthenticated]
    serializer_class = EducationSerializer
    
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Education list accessed - User ID: {user.id}")
        
        if user.role != 'job_seeker':
            logger.warning(f"Non-job-seeker user {user.id} attempted to access education")
            raise PermissionDenied({"error": "User is not a job seeker"})
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            return Education.objects.filter(job_seeker=job_seeker)
        except JobSeeker.DoesNotExist:
            logger.error(f"Job seeker profile not found for user {user.id}")
            raise NotFound({"error": "Job seeker profile not found"})
    
    def perform_create(self, serializer):
        user = self.request.user
        logger.info(f"Education creation attempt - User ID: {user.id}")
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            serializer.save(job_seeker=job_seeker)
            logger.info(f"Education created successfully - User ID: {user.id}")
        except JobSeeker.DoesNotExist:
            logger.error(f"Job seeker profile not found for user {user.id}")
            raise NotFound({"error": "Job seeker profile not found"})
        except Exception as e:
            logger.error(f"Education creation failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise

class EducationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete an education"""
    permission_classes = [IsAuthenticated]
    serializer_class = EducationSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role != 'job_seeker':
            raise PermissionDenied({"error": "User is not a job seeker"})
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            return Education.objects.filter(job_seeker=job_seeker)
        except JobSeeker.DoesNotExist:
            raise NotFound({"error": "Job seeker profile not found"})
    
    def perform_update(self, serializer):
        user = self.request.user
        logger.info(f"Education update attempt - User ID: {user.id}, Education ID: {self.kwargs.get('pk')}")
        try:
            serializer.save()
            logger.info(f"Education updated successfully - User ID: {user.id}")
        except Exception as e:
            logger.error(f"Education update failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise
    
    def perform_destroy(self, instance):
        user = self.request.user
        logger.info(f"Education deletion attempt - User ID: {user.id}, Education ID: {instance.id}")
        try:
            instance.delete()
            logger.info(f"Education deleted successfully - User ID: {user.id}")
        except Exception as e:
            logger.error(f"Education deletion failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise

# Skills Views
class SkillListCreateView(generics.ListCreateAPIView):
    """List and create skills for job seeker"""
    permission_classes = [IsAuthenticated]
    serializer_class = SkillSerializer
    
    def get_queryset(self):
        user = self.request.user
        logger.debug(f"Skill list accessed - User ID: {user.id}")
        
        if user.role != 'job_seeker':
            logger.warning(f"Non-job-seeker user {user.id} attempted to access skills")
            raise PermissionDenied({"error": "User is not a job seeker"})
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            return Skill.objects.filter(job_seeker=job_seeker)
        except JobSeeker.DoesNotExist:
            logger.error(f"Job seeker profile not found for user {user.id}")
            raise NotFound({"error": "Job seeker profile not found"})
    
    def perform_create(self, serializer):
        user = self.request.user
        logger.info(f"Skill creation attempt - User ID: {user.id}")
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            
            # Check if skill already exists for this job seeker
            skill_name = serializer.validated_data.get('name')
            if Skill.objects.filter(job_seeker=job_seeker, name=skill_name).exists():
                logger.warning(f"Duplicate skill attempt - User ID: {user.id}, Skill: {skill_name}")
                raise ValidationError({"error": f"Skill '{skill_name}' already exists"})
            
            serializer.save(job_seeker=job_seeker)
            logger.info(f"Skill created successfully - User ID: {user.id}, Skill: {skill_name}")
        except JobSeeker.DoesNotExist:
            logger.error(f"Job seeker profile not found for user {user.id}")
            raise NotFound({"error": "Job seeker profile not found"})
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Skill creation failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise

class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete a skill"""
    permission_classes = [IsAuthenticated]
    serializer_class = SkillSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role != 'job_seeker':
            raise PermissionDenied({"error": "User is not a job seeker"})
        
        try:
            job_seeker = JobSeeker.objects.get(user=user)
            return Skill.objects.filter(job_seeker=job_seeker)
        except JobSeeker.DoesNotExist:
            raise NotFound({"error": "Job seeker profile not found"})
    
    def perform_update(self, serializer):
        user = self.request.user
        logger.info(f"Skill update attempt - User ID: {user.id}, Skill ID: {self.kwargs.get('pk')}")
        try:
            serializer.save()
            logger.info(f"Skill updated successfully - User ID: {user.id}")
        except Exception as e:
            logger.error(f"Skill update failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise
    
    def perform_destroy(self, instance):
        user = self.request.user
        logger.info(f"Skill deletion attempt - User ID: {user.id}, Skill: {instance.name}")
        try:
            instance.delete()
            logger.info(f"Skill deleted successfully - User ID: {user.id}")
        except Exception as e:
            logger.error(f"Skill deletion failed - User ID: {user.id}, Error: {str(e)}", exc_info=True)
            raise

class RecruiterProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update recruiter profile with company details
    URL: /api/accounts/recruiter/profile/
    Methods: GET, PATCH
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecruiterProfileSerializer
        return RecruiterUpdateSerializer
    
    def get_object(self):
        user = self.request.user
        logger.debug(f"Recruiter profile accessed - User ID: {user.id}")
        
        if user.role != 'recruiter':
            logger.warning(f"Non-recruiter user {user.id} attempted to access recruiter profile")
            raise PermissionDenied({"error": "User is not a recruiter"})
        
        try:
            return Recruiter.objects.get(user=user)
        except Recruiter.DoesNotExist:
            logger.error(f"Recruiter profile not found for user {user.id}")
            raise NotFound({"error": "Recruiter profile not found"})
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Recruiter profile retrieved - User ID: {request.user.id}")
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        logger.info(f"Recruiter profile update attempt - User ID: {request.user.id}")
        try:
            response = super().update(request, *args, **kwargs)
            logger.info(f"Recruiter profile updated successfully - User ID: {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Recruiter profile update failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
            raise

class CompanyProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update company profile (for recruiters)
    URL: /api/accounts/recruiter/company/
    Methods: GET, PATCH
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = CompanyUpdateSerializer
    
    def get_object(self):
        user = self.request.user
        logger.debug(f"Company profile accessed - User ID: {user.id}")
        
        if user.role != 'recruiter':
            logger.warning(f"Non-recruiter user {user.id} attempted to access company profile")
            raise PermissionDenied({"error": "User is not a recruiter"})
        
        try:
            recruiter = Recruiter.objects.get(user=user)
            if not recruiter.company:
                logger.warning(f"Recruiter {user.id} has no company assigned")
                raise NotFound({"error": "No company assigned to this recruiter"})
            return recruiter.company
        except Recruiter.DoesNotExist:
            logger.error(f"Recruiter profile not found for user {user.id}")
            raise NotFound({"error": "Recruiter profile not found"})
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Company profile retrieved - User ID: {request.user.id}, Company: {instance.name}")
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        logger.info(f"Company profile update attempt - User ID: {request.user.id}")
        try:
            response = super().update(request, *args, **kwargs)
            logger.info(f"Company profile updated successfully - User ID: {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Company profile update failed - User ID: {request.user.id}, Error: {str(e)}", exc_info=True)
            raise

class PublicRecruiterProfileView(generics.RetrieveAPIView):
    """
    Simple public recruiter profile view
    URL: /api/accounts/recruiters/<int:pk>/public/
    """
    permission_classes = [AllowAny]
    serializer_class = RecruiterProfileSerializer
    
    def get_object(self):
        recruiter_id = self.kwargs.get('pk')
        logger.info(f"Public recruiter profile accessed - Recruiter ID: {recruiter_id}")
        
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id, user__is_active=True)
            logger.debug(f"Public recruiter profile found - Recruiter ID: {recruiter_id}")
            return recruiter
        except Recruiter.DoesNotExist:
            logger.warning(f"Public recruiter profile not found - Recruiter ID: {recruiter_id}")
            raise NotFound({"error": "Recruiter not found"})