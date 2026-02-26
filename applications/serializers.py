# applications/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Application, ApplicationNote, Interview,
    CandidateTag, CandidateCommunication
)
from accounts.models import JobSeeker
from jobs.models import Job

class ApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating applications"""
    class Meta:
        model = Application
        fields = [
            'status', 'match_score', 'recruiter_notes',
            'recruiter_rating', 'is_favorite', 'is_archived',
            'skills', 'experience_summary', 'interview_scheduled',
            'offer_made', 'offer_date', 'offer_details'
        ]
        
    
    def validate_match_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Match score must be between 0 and 100")
        return value


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    candidate_email = serializers.SerializerMethodField()
    candidate_phone = serializers.SerializerMethodField()
    candidate_location = serializers.SerializerMethodField()
    position_applied = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    last_active_display = serializers.SerializerMethodField()
    time_since_applied = serializers.SerializerMethodField()
    candidate_profile_picture = serializers.SerializerMethodField()

    # Interview info
    has_interview = serializers.BooleanField(source='has_scheduled_interview', read_only=True)
    interview_details = serializers.SerializerMethodField()
    
    # Add skill summary
    skill_summary = serializers.CharField(source='get_skill_summary', read_only=True)
    
    # FIX: Change from JSONField to SerializerMethodField for FileField
    resume_file = serializers.SerializerMethodField()
    
    # Add nested job serializer
    job_details = serializers.SerializerMethodField()
    seeker_details = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()

    interviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'job', 'seeker', 'status', 'status_display', 
            'applied_at', 'cover_letter', 'match_score', 'skills', 'skill_summary',
            'additional_info', 'last_active', 'last_active_display',
            'has_interview', 'interview_details','interviews','offer_made',
            'offer_date', 'offer_details', 'recruiter_notes',
            'recruiter_rating', 'is_favorite', 'is_archived',
            'messages_count', 'last_message_at', 'resume_file',
            'job_details', 'seeker_details', 'resume_url',
            'candidate_name', 'candidate_email', 'candidate_phone',
            'candidate_location', 'position_applied', 'time_since_applied', 'candidate_profile_picture',
        ]
        read_only_fields = ['applied_at', 'last_active', 'last_message_at']
    
    def get_interviews(self, obj):
        """Get all interviews for this application"""
        interviews = obj.interviews.all().order_by('-scheduled_date')
        return InterviewSerializer(interviews, many=True, context=self.context).data
    
    def get_interview_details(self, obj):
        """Get next interview details if exists"""
        interview = obj.next_interview
        if interview:
            return InterviewSerializer(interview, context=self.context).data
        return None
    
    def validate_skills(self, value):
        """Validate skills data structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a list")
        
        for skill in value:
            if not isinstance(skill, dict):
                raise serializers.ValidationError("Each skill must be a dictionary")
            if 'name' not in skill:
                raise serializers.ValidationError("Each skill must have a 'name' field")
            if 'rating' in skill:
                rating = skill['rating']
                if not isinstance(rating, int) or rating < 0 or rating > 5:
                    raise serializers.ValidationError("Rating must be an integer between 0 and 5")
        
        return value
    
    def validate_additional_info(self, value):
        """Validate additional_info data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Additional info must be a dictionary")
        return value
    

    def get_resume_file(self, obj):
        """Get resume file information for frontend"""
        if obj.resume_snapshot and obj.resume_snapshot.name:
            try:
                # Get the file URL
                file_url = obj.resume_snapshot.url
                file_name = obj.resume_snapshot.name.split('/')[-1]  # Extract filename
                
                return {
                    'url': file_url,
                    'name': file_name,
                    'size': obj.resume_snapshot.size if hasattr(obj.resume_snapshot, 'size') else 0,
                    'uploaded_at': obj.applied_at.isoformat(),
                    'type': self._get_file_type(file_name)
                }
            except:
                # If URL generation fails, return basic info
                return {
                    'name': obj.resume_snapshot.name.split('/')[-1] if obj.resume_snapshot.name else 'resume.pdf',
                    'url': None,
                    'error': 'File not accessible'
                }
        return None
    
    def _get_file_type(self, filename):
        """Determine file type from extension"""
        if filename.lower().endswith('.pdf'):
            return 'pdf'
        elif filename.lower().endswith(('.doc', '.docx')):
            return 'word'
        elif filename.lower().endswith(('.txt', '.text')):
            return 'text'
        elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return 'image'
        else:
            return 'document'
    
    def get_candidate_name(self, obj):
        return obj.candidate_name
    
    def get_candidate_email(self, obj):
        return obj.candidate_email
    
    def get_candidate_phone(self, obj):
        return obj.candidate_phone
    
    def get_candidate_location(self, obj):
        return obj.candidate_location
    
    def get_position_applied(self, obj):
        return obj.position_applied
    
    def get_time_since_applied(self, obj):
        delta = timezone.now() - obj.applied_at
        
        if delta.days > 0:
            return f"{delta.days} days ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def get_last_active_display(self, obj):
        if not obj.last_active:
            return "Never"
        
        delta = timezone.now() - obj.last_active
        
        if delta.days > 7:
            return obj.last_active.strftime("%b %d, %Y")
        elif delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def get_job_details(self, obj):
        """Get detailed job information"""
        if obj.job:
            # Safely get company info
            company_info = None
            if hasattr(obj.job, 'company'):
                if hasattr(obj.job.company, 'name'):
                    # If company is ForeignKey with name attribute
                    company_info = obj.job.company.name
                else:
                    # If company is CharField
                    company_info = obj.job.company
            
            # Safely get recruiter info
            recruiter_info = None
            if hasattr(obj.job, 'recruiter'):
                if hasattr(obj.job.recruiter, 'user'):
                    # If recruiter is ForeignKey to Recruiter model
                    recruiter_info = {
                        'id': obj.job.recruiter.id,
                        'name': obj.job.recruiter.user.get_full_name(),
                        'email': obj.job.recruiter.user.email,
                    }
                else:
                    # If recruiter is CharField
                    recruiter_info = obj.job.recruiter
            
            return {
                'id': obj.job.id,
                'title': obj.job.title,
                'company': company_info or 'No Company',
                'company_details': company_info,
                'recruiter': recruiter_info,
                'location': obj.job.location,
                'remote_policy': obj.job.remote_policy,
                'job_type': obj.job.job_type,
                'experience_level': obj.job.experience_level,
                'salary_min': getattr(obj.job, 'salary_min', None),
                'salary_max': getattr(obj.job, 'salary_max', None),
                'salary_display': getattr(obj.job, 'get_salary_display', lambda: 'Competitive')(),
                'description': obj.job.description,
                'requirements': obj.job.requirements,
                'created_at': obj.job.created_at,
                'is_active': obj.job.is_active,
            }
        return None
    
    
    def get_seeker_details(self, obj):
        """Get job seeker details"""
        if obj.seeker:
            return {
                'id': obj.seeker.id,
                'bio': obj.seeker.bio,
                'resume': obj.seeker.resume.url if obj.seeker.resume else None,
                'dob': obj.seeker.dob,
                'education': [],  # Add if you have education model
                'experience': [],  # Add if you have experience model
                'projects': [],    # Add if you have projects model
            }
        return None
    
    def get_resume_url(self, obj):
        """Get resume URL"""
        if obj.seeker and obj.seeker.resume:
            return obj.seeker.resume.url
        return None
    def get_candidate_profile_picture(self, obj):
        if obj.seeker and obj.seeker.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.seeker.profile_picture.url)
            return obj.seeker.profile_picture.url
        return None
        
class ApplicationNoteSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source='recruiter.user.get_full_name', read_only=True)
    
    class Meta:
        model = ApplicationNote
        fields = ['id', 'application', 'recruiter', 'recruiter_name',
                 'note', 'created_at', 'is_private']
        read_only_fields = ['recruiter', 'created_at']

class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='application.candidate_name', read_only=True)
    candidate_email = serializers.CharField(source='application.candidate_email', read_only=True)
    
    class Meta:
        model = Interview
        fields = '__all__'
    
    def validate_scheduled_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Interview cannot be scheduled in the past")
        return value

class CandidateTagSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = CandidateTag
        fields = ['id', 'application', 'tag', 'color', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_by', 'created_at']

class CandidateCommunicationSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source='recruiter.user.get_full_name', read_only=True)
    
    class Meta:
        model = CandidateCommunication
        fields = '__all__'
        read_only_fields = ['recruiter', 'sent_at']

# Update the JobSeekerApplicationSerializer
class JobSeekerApplicationSerializer(serializers.ModelSerializer):
    """Serializer for job seeker viewing their own applications"""
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company', read_only=True)
    company_logo = serializers.SerializerMethodField()
    job_location = serializers.CharField(source='job.location', read_only=True)
    job_type = serializers.CharField(source='job.job_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    applied_date = serializers.DateTimeField(source='applied_at', format='%Y-%m-%d', read_only=True)
    days_since_applied = serializers.SerializerMethodField()
    recruiter_name = serializers.SerializerMethodField()
    conversation_id = serializers.SerializerMethodField()
    resume_file = serializers.SerializerMethodField()
    skills = serializers.JSONField(read_only=True)
    additional_info = serializers.JSONField(read_only=True)
    profile_picture = serializers.SerializerMethodField()
    
    # Interview properties - using the Interview model
    has_interview = serializers.BooleanField(source='has_scheduled_interview', read_only=True)
    interview_details = serializers.SerializerMethodField()

    interviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'job', 'job_title', 'company_name', 'company_logo',
            'job_location', 'job_type', 'status', 'status_display',
            'applied_date', 'days_since_applied', 'match_score',
            'cover_letter', 'has_interview', 'interview_details', 'interviews',
            'offer_made', 'offer_date', 'recruiter_name', 
            'conversation_id', 'resume_file', 'skills', 'additional_info','profile_picture',
        ]
        read_only_fields = fields
    
    def get_interviews(self, obj):
        """Get all interviews for this application"""
        interviews = obj.interviews.all().order_by('-scheduled_date')
        return InterviewSerializer(interviews, many=True, context=self.context).data
    
    def get_interview_details(self, obj):
        """Get the next scheduled interview details"""
        interview = obj.next_interview
        if interview:
            from .serializers import InterviewSerializer
            return InterviewSerializer(interview, context=self.context).data
        return None
    
    def get_company_logo(self, obj):
        """Get company logo if available"""
        if hasattr(obj.job, 'company_logo') and obj.job.company_logo:
            return obj.job.company_logo.url
        return None
    
    def get_days_since_applied(self, obj):
        """Calculate days since application"""
        delta = timezone.now() - obj.applied_at
        return delta.days
    
    def get_recruiter_name(self, obj):
        """Get recruiter name"""
        if obj.job.recruiter and obj.job.recruiter.user:
            return obj.job.recruiter.user.get_full_name()
        return None
    
    def get_conversation_id(self, obj):
        """Get conversation ID if exists"""
        from chat.models import Conversation
        try:
            conversation = Conversation.objects.filter(
                application=obj,
                job_seeker=obj.seeker
            ).first()
            return conversation.id if conversation else None
        except:
            return None
    def get_profile_picture(self, obj):
        if obj.seeker and obj.seeker.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.seeker.profile_picture.url)
            return obj.seeker.profile_picture.url
        return None
    
    def get_resume_file(self, obj):
        """Get resume file information from resume_snapshot"""
        if obj.resume_snapshot and obj.resume_snapshot.name:
            try:
                request = self.context.get('request')
                file_url = obj.resume_snapshot.url
                
                # Get file info
                file_name = obj.resume_snapshot.name.split('/')[-1]
                file_size = obj.resume_snapshot.size if hasattr(obj.resume_snapshot, 'size') else None
                
                # Determine file type
                if file_name.lower().endswith('.pdf'):
                    file_type = 'pdf'
                elif file_name.lower().endswith(('.doc', '.docx')):
                    file_type = 'word'
                elif file_name.lower().endswith(('.txt', '.text')):
                    file_type = 'text'
                elif file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    file_type = 'image'
                else:
                    file_type = 'document'
                
                return {
                    'url': request.build_absolute_uri(file_url) if request else file_url,
                    'name': file_name,
                    'type': file_type,
                    'size': file_size,
                    'uploaded_at': obj.applied_at.isoformat(),
                    'is_available': True
                }
            except Exception as e:
                print(f"Error getting resume file: {e}")
                return {
                    'name': obj.resume_snapshot.name.split('/')[-1] if obj.resume_snapshot.name else 'resume.pdf',
                    'url': None,
                    'error': 'File not accessible',
                    'is_available': False
                }
        
        # Check if seeker has a resume as fallback
        elif obj.seeker and obj.seeker.resume:
            request = self.context.get('request')
            return {
                'url': request.build_absolute_uri(obj.seeker.resume.url) if request else obj.seeker.resume.url,
                'name': obj.seeker.resume.name.split('/')[-1] if obj.seeker.resume.name else 'resume.pdf',
                'type': 'pdf',
                'is_available': True
            }
        
        return None
    

class ApplicationBasicSerializer(serializers.ModelSerializer):
    """Basic application information serializer"""
    job_title = serializers.CharField(source='job.title', read_only=True)
    candidate_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'job', 'job_title', 'seeker', 'status',
            'applied_at', 'match_score', 'candidate_name'
        ]
        read_only_fields = fields
    
    def get_candidate_name(self, obj):
        return obj.candidate_name
    
    def get_profile_picture(self, obj):
        if obj.seeker and obj.seeker.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.seeker.profile_picture.url)
            return obj.seeker.profile_picture.url
        return None