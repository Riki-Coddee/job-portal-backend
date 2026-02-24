# companies/models.py
from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    description = models.TextField()
    website = models.URLField(max_length=200, blank=True)
    industry = models.CharField(max_length=100, help_text="e.g. Technology, Healthcare")
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # New fields for detailed company profile
    tagline = models.CharField(max_length=255, blank=True, help_text="Company tagline")
    headquarters = models.CharField(max_length=255, blank=True, help_text="Full address of headquarters")
    founded_year = models.IntegerField(null=True, blank=True)
    company_size = models.CharField(max_length=50, blank=True, help_text="e.g., 51-200 employees")
    email = models.EmailField(blank=True, help_text="Contact email")
    phone = models.CharField(max_length=20, blank=True, help_text="Contact phone")
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    
    # Company perks/benefits (store as JSON or related model)
    perks = models.JSONField(default=list, blank=True, help_text="List of company perks")
    
    # Company culture/awards
    culture_description = models.TextField(blank=True, help_text="Company culture description")
    awards = models.JSONField(default=list, blank=True, help_text="List of awards")
    
    class Meta:
        verbose_name_plural = "Companies"
    
    def __str__(self):
        return self.name

    @property
    def total_recruiters(self):
        """Get total number of recruiters for this company"""
        return self.recruiters.count()