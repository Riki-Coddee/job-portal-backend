from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.exceptions import ValidationError
from companies.models import Company  # Import the Company model

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        RECRUITER = "recruiter", "Recruiter"
        JOBSEEKER = "job_seeker", "Job Seeker"

    username = None
    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.JOBSEEKER)

    # Add these fields for online tracking
    last_activity = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def update_activity(self):
        """Update user's last activity time"""
        self.last_activity = timezone.now()
        self.is_online = True
        self.save(update_fields=['last_activity', 'is_online'])
    
    def get_online_status(self):
        """Check if user is considered online (active in last 5 minutes)"""
        if not self.last_activity:
            return False
        # Consider online if last activity within last 5 minutes
        time_diff = timezone.now() - self.last_activity
        return time_diff.total_seconds() < 300  # 5 minutes
    
# Update JobSeeker model with new fields
class JobSeeker(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="seeker_profile")
    dob = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        null=True, 
        blank=True
    )
    # New fields
    title = models.CharField(max_length=200, blank=True, help_text="Professional title")
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    portfolio_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)

    def clean(self):
        if self.user.role != CustomUser.Roles.JOBSEEKER:
            raise ValidationError("User must have the 'job_seeker' role.")

    def __str__(self):
        return self.user.email
    
  
class Experience(models.Model):
    job_seeker = models.ForeignKey(
        JobSeeker, 
        on_delete=models.CASCADE, 
        related_name="experiences"
    )
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    currently_working = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} at {self.company}"

class Education(models.Model):
    job_seeker = models.ForeignKey(
        JobSeeker, 
        on_delete=models.CASCADE, 
        related_name="educations"
    )
    degree = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    currently_studying = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.degree} at {self.institution}"

class Skill(models.Model):
    job_seeker = models.ForeignKey(
        JobSeeker, 
        on_delete=models.CASCADE, 
        related_name="skills"
    )
    name = models.CharField(max_length=100)
    proficiency = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ],
        default='intermediate'
    )

    class Meta:
        unique_together = ['job_seeker', 'name']

    def __str__(self):
        return self.name

  
class Recruiter(models.Model):
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name="recruiter"
    )
    # Link to the Company model instead of using CharFields
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name="recruiters",
        null=True, 
        blank=True
    )
    designation = models.CharField(
        max_length=100, 
        help_text="e.g. HR Manager, Talent Acquisition"
    )
    phone_number = models.CharField(max_length=15)
    profile_picture = models.ImageField(
        upload_to='recruiter_profile_pictures/', 
        null=True, 
        blank=True
    )
    bio = models.TextField(blank=True, help_text="Recruiter bio/introduction")
    department = models.CharField(max_length=100, blank=True, help_text="Department")

    def __str__(self):
        # Access company name through the relationship
        company_name = self.company.name if self.company else "No Company Assigned"
        return f"{self.user.email} - {company_name} ({self.designation})"

