from django.contrib import admin
from .models import Resume, WorkExperience, Education, Skill

class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 1

class EducationInline(admin.TabularInline):
    model = Education
    extra = 1

class SkillInline(admin.TabularInline):
    model = Skill
    extra = 3

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('seeker', 'summary_snippet')
    inlines = [WorkExperienceInline, EducationInline, SkillInline]

    def summary_snippet(self, obj):
        return obj.summary[:50] + "..." if obj.summary else "No summary"