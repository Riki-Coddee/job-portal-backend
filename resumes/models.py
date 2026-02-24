from django.db import models
from accounts.models import JobSeeker

class Resume(models.Model):
    seeker = models.OneToOneField(JobSeeker, on_delete=models.CASCADE, related_name="detailed_resume")
    summary = models.TextField(blank=True, help_text="Professional summary")
    upload_file = models.FileField(upload_to="resumes/pdfs/", null=True, blank=True)

    def __str__(self):
        return f"Resume of {self.seeker.user.email}"

class WorkExperience(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="experience")
    company_name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if currently working")
    description = models.TextField()

class Education(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255)
    graduation_year = models.IntegerField()

class Skill(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name