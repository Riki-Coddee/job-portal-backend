# models.py
from django.db import models
from django.utils.text import slugify
from accounts.models import Recruiter
from django.utils import timezone


class JobSkill(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, blank=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'


class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('temporary', 'Temporary'),
    ]

    REMOTE_CHOICES = [
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ]

    EXPERIENCE_CHOICES = [
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior'),
        ('executive', 'Executive'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('CAD', 'Canadian Dollar'),
        ('NPR', 'Nepali Rupee (Rs.)'),
    ]
 
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='jobs')
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    remote_policy = models.CharField(max_length=20, choices=REMOTE_CHOICES, default='onsite')
    
    # Salary fields
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='NPR')
    display_salary = models.BooleanField(default=True)
    
    # Experience
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='mid')
    
    requirements = models.TextField()
    benefits = models.TextField(blank=True)
    
    # Status and scheduling
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    # Scheduling
    publish_option = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Publish Immediately'),
            ('schedule', 'Schedule for Later')
        ],
        default='immediate'
    )
    scheduled_date = models.DateTimeField(null=True, blank=True)

    # Skills
    skills = models.ManyToManyField(JobSkill, related_name='jobs', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} at {self.recruiter.company.name}"
    
    def save(self, *args, **kwargs):
        # Auto-set company if not provided
        if not self.company and hasattr(self.recruiter, 'company_name'):
            self.company = self.recruiter.company.name
        
        # Handle publication logic
        if self.publish_option == 'immediate' and not self.published_at:
            self.is_published = True
            self.published_at = timezone.now()
            if not self.scheduled_date:
                self.scheduled_date = timezone.now()
        elif self.publish_option == 'schedule' and self.scheduled_date:
            self.is_published = self.scheduled_date <= timezone.now()
            if self.is_published and not self.published_at:
                self.published_at = timezone.now()
        
        # Set default expiry (30 days from publication)
        if self.is_published and not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        super().save(*args, **kwargs)

    @property
    def salary_display(self):
        if self.salary_min and self.salary_max:
            return f"{self.currency} {self.salary_min:,.0f} - {self.salary_max:,.0f}"
        elif self.salary_min:
            return f"{self.currency} {self.salary_min:,.0f}+"
        return "Competitive Salary"
    
    @property
    def is_scheduled(self):
        return self.publish_option == 'schedule' and self.scheduled_date > timezone.now()
    
    class Meta:
        ordering = ['-created_at']