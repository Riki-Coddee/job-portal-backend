# serializers.py (keep only serializers)
from rest_framework import serializers
from .models import Job, JobSkill, Department
from django.utils import timezone

class JobSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSkill
        fields = ['id', 'name']

class JobSerializer(serializers.ModelSerializer):
    salary_display = serializers.ReadOnlyField()
    is_scheduled = serializers.ReadOnlyField()
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False
    )
    skills_display = serializers.SerializerMethodField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'description', 'location',
            'job_type', 'remote_policy', 'salary_min', 'salary_max',
            'currency', 'display_salary', 'experience_level',
            'requirements', 'benefits', 'skills', 'skills_display',
            'is_active', 'is_published', 'is_featured', 'publish_option', 
            'scheduled_date', 'published_at', 'expires_at', 'salary_display',
            'is_scheduled', 'created_at', 'department', 'department_name'
        ]
        read_only_fields = ['recruiter', 'published_at', 'is_published', 'department_name', 'skills_display']
    
    def get_skills_display(self, obj):
        # Return array of skill names for display
        return list(obj.skills.values_list('name', flat=True))
    
    def validate_scheduled_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Scheduled date must be in the future.")
        return value
    
    def validate(self, data):
        # Validate salary range
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise serializers.ValidationError({
                'salary_min': 'Minimum salary cannot be greater than maximum salary.'
            })
        
        return data
    
    def create(self, validated_data):
        # Extract skills from validated_data
        skills_data = validated_data.pop('skills', [])
        
        # Create the job
        job = Job.objects.create(**validated_data)
        
        # Process and add skills
        if skills_data:
            skills_to_add = []
            for skill_name in skills_data:
                if skill_name and skill_name.strip():
                    skill, created = JobSkill.objects.get_or_create(
                        name=skill_name.strip().lower()
                    )
                    skills_to_add.append(skill)
            
            # Add skills to the job
            if skills_to_add:
                job.skills.set(skills_to_add)
        
        return job
    
    def update(self, instance, validated_data):
        # Extract skills from validated_data
        skills_data = validated_data.pop('skills', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update skills if provided
        if skills_data is not None:
            skills_to_add = []
            for skill_name in skills_data:
                if skill_name and skill_name.strip():
                    skill, created = JobSkill.objects.get_or_create(
                        name=skill_name.strip().lower()
                    )
                    skills_to_add.append(skill)
            
            # Update the job's skills
            if skills_to_add:
                instance.skills.set(skills_to_add)
            else:
                instance.skills.clear()
        
        return instance
# Add a simplified serializer for featured jobs if needed
class FeaturedJobSerializer(serializers.ModelSerializer):
    skills = JobSkillSerializer(many=True, read_only=True)
    salary_display = serializers.ReadOnlyField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'description', 'location',
            'job_type', 'remote_policy', 'salary_display', 'experience_level',
            'is_featured', 'published_at', 'department', 'skills'
        ]


class JobBasicSerializer(serializers.ModelSerializer):
    """Basic job information serializer"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'company_name', 'location',
            'job_type', 'remote_policy', 'experience_level',
            'is_active', 'is_published'
        ]
        read_only_fields = fields

class DepartmentSerializer(serializers.ModelSerializer):
    """Simple serializer for department GET requests"""
    job_count = serializers.IntegerField(source='jobs.count', read_only=True)
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'slug', 'is_active', 'job_count']
        read_only_fields = ['id', 'name', 'slug', 'is_active', 'job_count']
