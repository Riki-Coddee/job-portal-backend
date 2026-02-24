from rest_framework import serializers
from .models import JobSeeker, Recruiter, Company, Skill, Education, Experience
from companies.models import Company
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from django.core.exceptions import ValidationError

User = get_user_model()

# accounts/serializers.py - Fix the UserRegistrationSerializer validation

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField(max_length=15, write_only=True)
    location = serializers.CharField(required=False, allow_blank=True, write_only=True)
    company = serializers.IntegerField(required=False, write_only=True, allow_null=True)  # Company ID for recruiter only
    designation = serializers.CharField(required=False, allow_blank=True, write_only=True)
    is_existing_user = serializers.BooleanField(default=False, write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 
                 'role', 'phone_number', 'location', 'company', 
                 'designation', 'is_existing_user']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {
                'required': True,
                'validators': []  # REMOVE the default unique validator
            }
        }
    
    def validate(self, data):
        email = data.get('email')
        role = data.get('role')
        password = data.get('password')
        is_existing_user = data.get('is_existing_user', False)
        
        # Validate role
        valid_roles = [choice[0] for choice in User.Roles.choices]
        if role not in valid_roles:
            raise serializers.ValidationError({
                'error': f'Invalid role. Must be one of: {valid_roles}'
            })
        
        # Check if user exists
        user_exists = User.objects.filter(email=email).exists()
        
        if user_exists:
            existing_user = User.objects.get(email=email)
            
            # If user is checking if they exist (frontend logic)
            if is_existing_user:
                # Verify password
                user = authenticate(username=email, password=password)
                if not user:
                    raise serializers.ValidationError({
                        'error': 'Incorrect password for existing account'
                    })
                
                # Check if already has this role
                if existing_user.role == role:
                    raise serializers.ValidationError({
                        'error': f'You are already registered as a {role}'
                    })
                
                # Allow role change
                data['existing_user'] = existing_user
                return data
            
            else:
                # Regular registration attempt - user exists
                raise serializers.ValidationError({
                    'error': f'User with this email already exists as {existing_user.role}'
                })
        
        # New user validation - ONLY require company for recruiters
        if role == 'recruiter':
            company = data.get('company')
            if not company:
                raise serializers.ValidationError({
                    'error': 'Company is required for recruiters'
                })
            if not Company.objects.filter(id=company).exists():
                raise serializers.ValidationError({
                    'error': 'Company does not exist'
                })
            if not data.get('designation'):
                raise serializers.ValidationError({
                    'error': 'Designation is required for recruiters'
                })
        else:
            # For job seekers, remove company field if present
            if 'company' in data:
                data.pop('company')
            if 'designation' in data:
                data.pop('designation')
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        is_existing_user = validated_data.pop('is_existing_user', False)
        existing_user = validated_data.pop('existing_user', None)
        
        # Extract profile data
        phone_number = validated_data.pop('phone_number')
        location = validated_data.pop('location', '')
        company_id = validated_data.pop('company', None)  # Will be None for job seekers
        designation = validated_data.pop('designation', '')
        role = validated_data.get('role')
        
        if is_existing_user and existing_user:
            # Handle role change for existing user
            user = existing_user
            
            # Update user fields if provided
            user.first_name = validated_data.get('first_name', user.first_name)
            user.last_name = validated_data.get('last_name', user.last_name)
            user.role = role
            user.save()
            
            # Delete old profile if exists
            if role == 'recruiter':
                # Remove old job seeker profile
                JobSeeker.objects.filter(user=user).delete()
                company = Company.objects.get(id=company_id)
                Recruiter.objects.update_or_create(
                    user=user,
                    defaults={
                        'company': company,
                        'designation': designation,
                        'phone_number': phone_number
                    }
                )
            elif role == 'job_seeker':
                # Remove old recruiter profile
                Recruiter.objects.filter(user=user).delete()
                JobSeeker.objects.update_or_create(
                    user=user,
                    defaults={
                        'phone_number': phone_number,
                        'location': location
                    }
                )
            
            return user
        
        else:
            # Create new user
            user = User.objects.create_user(**validated_data)
            
            # Create role-specific profile
            if role == 'job_seeker':
                JobSeeker.objects.create(
                    user=user,
                    phone_number=phone_number,
                    location=location
                )
            elif role == 'recruiter':
                company = Company.objects.get(id=company_id)
                Recruiter.objects.create(
                    user=user,
                    company=company,
                    designation=designation,
                    phone_number=phone_number
                )
            
            return user

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to response
        data.update({
            'role': self.user.role,
            'email': self.user.email,
            'full_name': self.user.get_full_name(),
            'user_id': self.user.id,
        })
        
        # Add role-specific data if needed
        if self.user.role == 'recruiter' and hasattr(self.user, 'recruiter'):
            data['company'] = self.user.recruiter.company.name
            data['designation'] = self.user.recruiter.designation
        
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add role to JWT payload
        token['role'] = user.role
        token['email'] = user.email
        return token
    
    
class PasswordChangeSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(required=True)
    newPassword = serializers.CharField(required=True, validators=[validate_password])


class CurrentRecruiterSerializer(serializers.ModelSerializer):
    """Serializer for current recruiter with full details"""
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    location = serializers.CharField(source='user.location', read_only=True)
    
    company_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Recruiter
        fields = [
            'id',
            'email',
            'first_name', 
            'last_name',
            'phone_number',
            'location',
            'designation',
            'company',
            'company_details'
        ]
    
    def get_company_details(self, obj):
        """Get detailed company info"""
        if obj.company:
            return {
                'id': obj.company.id,
                'name': obj.company.name,
                'logo': obj.company.logo.url if obj.company.logo else None,
                'description': obj.company.description,
                'website': obj.company.website,
                'industry': obj.company.industry,
                'location': obj.company.location,
            }
        return None
    

# Add to accounts/serializers.py, after the existing serializers

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information serializer"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role']
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class RecruiterBasicSerializer(serializers.ModelSerializer):
    """Basic recruiter information serializer"""
    user = UserBasicSerializer(read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = Recruiter
        fields = ['id', 'user', 'company', 'company_name', 'designation', 'phone_number']


class JobSeekerBasicSerializer(serializers.ModelSerializer):
    """Basic job seeker information serializer"""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = JobSeeker
        fields = ['id', 'user', 'phone_number', 'location', 'bio']


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ['id', 'title', 'company', 'location', 'start_date', 
                 'end_date', 'currently_working', 'description']
        read_only_fields = ['id', 'job_seeker']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'degree', 'institution', 'field_of_study', 
                 'start_date', 'end_date', 'currently_studying', 'description']
        read_only_fields = ['id', 'job_seeker']

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'proficiency']
        read_only_fields = ['id', 'job_seeker']

class JobSeekerProfileSerializer(serializers.ModelSerializer):
    """Serializer for job seeker profile"""
    user = UserBasicSerializer(read_only=True)
    experiences = ExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    
    class Meta:
        model = JobSeeker
        fields = [
            'id', 'user', 'dob', 'phone_number', 'bio', 'location',
            'profile_picture', 'title', 'resume', 'portfolio_url',
            'github_url', 'linkedin_url', 'experiences', 'educations', 'skills'
        ]
        read_only_fields = ['id', 'user']

class JobSeekerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating job seeker profile"""
    class Meta:
        model = JobSeeker
        fields = [
            'title', 'bio', 'location', 'phone_number', 'dob',
            'profile_picture', 'resume', 'portfolio_url',
            'github_url', 'linkedin_url'
        ]
        extra_kwargs = {
            'profile_picture': {'required': False},
            'resume': {'required': False},
        }


# accounts/serializers.py - Add Recruiter serializers
class RecruiterProfileSerializer(serializers.ModelSerializer):
    """Serializer for recruiter profile with company details"""
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    company_details = serializers.SerializerMethodField()
    profile_completion = serializers.SerializerMethodField()
    
    class Meta:
        model = Recruiter
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'profile_picture',
            'designation',
            'department',
            'bio',
            'company',
            'company_details',
            'profile_completion'
        ]
        read_only_fields = ['id', 'email', 'first_name', 'last_name']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    
    def get_company_details(self, obj):
        if obj.company:
            return {
                'id': obj.company.id,
                'name': obj.company.name,
                'logo': obj.company.logo.url if obj.company.logo else None,
                'description': obj.company.description,
                'tagline': obj.company.tagline,
                'website': obj.company.website,
                'industry': obj.company.industry,
                'location': obj.company.location,
                'headquarters': obj.company.headquarters,
                'founded_year': obj.company.founded_year,
                'company_size': obj.company.company_size,
                'email': obj.company.email,
                'phone': obj.company.phone,
                'linkedin_url': obj.company.linkedin_url,
                'twitter_url': obj.company.twitter_url,
                'facebook_url': obj.company.facebook_url,
                'instagram_url': obj.company.instagram_url,
                'perks': obj.company.perks,
                'culture_description': obj.company.culture_description,
                'awards': obj.company.awards,
                'total_recruiters': obj.company.total_recruiters,
            }
        return None
    
    def get_profile_completion(self, obj):
        """Calculate recruiter profile completion"""
        completion = calculate_recruiter_completion(obj)
        return completion

class RecruiterUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating recruiter profile"""
    class Meta:
        model = Recruiter
        fields = [
            'profile_picture',
            'phone_number',
            'designation',
            'department',
            'bio'
        ]

class CompanyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating company profile"""
    class Meta:
        model = Company
        fields = [
            'name',
            'logo',
            'description',
            'tagline',
            'website',
            'industry',
            'location',
            'headquarters',
            'founded_year',
            'company_size',
            'email',
            'phone',
            'linkedin_url',
            'twitter_url',
            'facebook_url',
            'instagram_url',
            'perks',
            'culture_description',
            'awards'
        ]

def calculate_recruiter_completion(recruiter):
    """Calculate profile completion percentage for recruiter"""
    sections = {
        'basic_info': ['phone_number', 'designation', 'bio'],
        'company_basic': ['name', 'description', 'industry', 'location'],
        'company_details': ['website', 'company_size', 'email'],
        'company_social': ['linkedin_url'],
        'company_culture': ['perks', 'culture_description']
    }
    
    total_points = 0
    earned_points = 0
    
    # Recruiter Basic Info (20% weight)
    for field in sections['basic_info']:
        total_points += 6.67
        if field == 'bio':
            if getattr(recruiter, field) and len(getattr(recruiter, field)) > 30:
                earned_points += 6.67
        elif getattr(recruiter, field):
            earned_points += 6.67
    
    # Company Basic Info (40% weight)
    if recruiter.company:
        for field in sections['company_basic']:
            total_points += 10
            if getattr(recruiter.company, field):
                earned_points += 10
    
    # Company Details (20% weight)
    if recruiter.company:
        for field in sections['company_details']:
            total_points += 6.67
            if getattr(recruiter.company, field):
                earned_points += 6.67
    
    # Company Social (10% weight)
    if recruiter.company:
        for field in sections['company_social']:
            total_points += 10
            if getattr(recruiter.company, field):
                earned_points += 10
    
    # Company Culture (10% weight)
    if recruiter.company:
        for field in sections['company_culture']:
            total_points += 5
            if field == 'perks':
                if getattr(recruiter.company, field) and len(getattr(recruiter.company, field)) > 0:
                    earned_points += 5
            elif getattr(recruiter.company, field):
                earned_points += 5
    
    percentage = (earned_points / total_points) * 100 if total_points > 0 else 0
    
    # Get checklist
    checklist = [
        {
            'id': 1,
            'label': 'Complete your recruiter bio',
            'completed': bool(recruiter.bio and len(recruiter.bio) > 30),
            'weight': 6.67,
            'field': 'recruiter_bio'
        },
        {
            'id': 2,
            'label': 'Add your designation',
            'completed': bool(recruiter.designation),
            'weight': 6.67,
            'field': 'designation'
        },
        {
            'id': 3,
            'label': 'Add phone number',
            'completed': bool(recruiter.phone_number),
            'weight': 6.67,
            'field': 'phone_number'
        },
        {
            'id': 4,
            'label': 'Complete company name',
            'completed': bool(recruiter.company and recruiter.company.name),
            'weight': 10,
            'field': 'company_name'
        },
        {
            'id': 5,
            'label': 'Add company description',
            'completed': bool(recruiter.company and recruiter.company.description),
            'weight': 10,
            'field': 'company_description'
        },
        {
            'id': 6,
            'label': 'Add company industry',
            'completed': bool(recruiter.company and recruiter.company.industry),
            'weight': 10,
            'field': 'company_industry'
        },
        {
            'id': 7,
            'label': 'Add company location',
            'completed': bool(recruiter.company and recruiter.company.location),
            'weight': 10,
            'field': 'company_location'
        },
        {
            'id': 8,
            'label': 'Add company website',
            'completed': bool(recruiter.company and recruiter.company.website),
            'weight': 6.67,
            'field': 'company_website'
        },
        {
            'id': 9,
            'label': 'Add company size',
            'completed': bool(recruiter.company and recruiter.company.company_size),
            'weight': 6.67,
            'field': 'company_size'
        },
        {
            'id': 10,
            'label': 'Add company contact email',
            'completed': bool(recruiter.company and recruiter.company.email),
            'weight': 6.67,
            'field': 'company_email'
        },
        {
            'id': 11,
            'label': 'Add LinkedIn URL',
            'completed': bool(recruiter.company and recruiter.company.linkedin_url),
            'weight': 10,
            'field': 'company_linkedin'
        },
        {
            'id': 12,
            'label': 'Add company perks',
            'completed': bool(recruiter.company and recruiter.company.perks and len(recruiter.company.perks) > 0),
            'weight': 5,
            'field': 'company_perks'
        },
        {
            'id': 13,
            'label': 'Describe company culture',
            'completed': bool(recruiter.company and recruiter.company.culture_description),
            'weight': 5,
            'field': 'company_culture'
        }
    ]
    
    return {
        'percentage': round(percentage),
        'checklist': checklist
    }


class PublicRecruiterProfileSerializer(serializers.ModelSerializer):
    """Serializer for public recruiter profile (for job seekers)"""
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = Recruiter
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'profile_picture',
            'designation',
            'department',
            'bio',
            'company',
            'company_name'
        ]
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()