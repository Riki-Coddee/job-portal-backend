from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import CustomUser, JobSeeker, Recruiter, Experience, Education, Skill
from .forms import CustomUserCreationForm, CustomUserChangeForm


# ========== INLINE CLASSES ==========
class ExperienceInline(admin.TabularInline):
    """Simplified experience inline"""
    model = Experience
    extra = 0  # Changed from 1 to 0 to prevent adding new ones
    fields = ('title', 'company', 'start_date', 'end_date', 'currently_working')
    verbose_name = "Work Experience"
    verbose_name_plural = "Work Experiences"
    can_delete = False  # Disable delete
    show_change_link = True  # Allow viewing but not editing directly
    max_num = 0  # Prevent adding new ones


class EducationInline(admin.TabularInline):
    """Simplified education inline"""
    model = Education
    extra = 0
    fields = ('degree', 'institution', 'start_date', 'end_date', 'currently_studying')
    verbose_name = "Education"
    verbose_name_plural = "Education"
    can_delete = False
    show_change_link = True
    max_num = 0


class SkillInline(admin.TabularInline):
    """Simplified skills inline"""
    model = Skill
    extra = 0
    fields = ('name', 'proficiency')
    verbose_name = "Skill"
    verbose_name_plural = "Skills"
    can_delete = False
    show_change_link = True
    max_num = 0


# ========== CUSTOM USER ADMIN ==========
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """User-friendly admin for CustomUser model"""
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = CustomUser
    
    # Clean list display - show only what matters
    list_display = (
        'email',
        'full_name',
        'role_badge',
        'status_badge',
        'joined_date',
    )
    
    list_filter = (
        'role',
        'is_active',
    )
    
    search_fields = (
        'email',
        'first_name',
        'last_name',
    )
    
    ordering = ('-date_joined',)
    list_per_page = 25
    
    # Simplified fieldsets for better UX
    fieldsets = (
        ('👤 Basic Information', {
            'fields': ('email', 'first_name', 'last_name', 'role'),
            'description': 'Core user information'
        }),
        ('🔐 Account Security', {
            'fields': ('password',),
            'classes': ('wide',),
            'description': 'Change password (leave blank to keep current)'
        }),
        ('⚙️ Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    # Helper methods for better display
    def full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else "—"
    full_name.short_description = 'Name'
    
    def role_badge(self, obj):
        colors = {
            'admin': 'purple',
            'recruiter': 'blue',
            'job_seeker': 'green',
        }
        color = colors.get(obj.role, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.8em;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.8em;">✅ Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.8em;">⛔ Inactive</span>'
        )
    status_badge.short_description = 'Status'
    
    def joined_date(self, obj):
        return obj.date_joined.strftime('%b %d, %Y')
    joined_date.short_description = 'Joined'
    joined_date.admin_order_field = 'date_joined'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seeker_profile', 'recruiter')


# ========== JOB SEEKER ADMIN ==========
@admin.register(JobSeeker)
class JobSeekerAdmin(admin.ModelAdmin):
    """Clean and simple JobSeeker admin"""
    
    list_display = (
        'name',
        'email',
        'title',
        'location',
        'quick_stats',
    )
    
    list_filter = (
        'location',
        'user__is_active',
    )
    
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'title',
        'location'
    )
    
    fieldsets = (
        ('👤 Profile Overview', {
            'fields': ('user', 'title', 'bio', 'location'),
            'description': 'Basic profile information'
        }),
        ('📞 Contact', {
            'fields': ('phone_number',),
            'classes': ('wide',)
        }),
        ('🔗 Online Presence', {
            'fields': ('linkedin_url', 'github_url', 'portfolio_url'),
            'classes': ('collapse',),
            'description': 'Social and professional links'
        }),
    )
    
    inlines = [ExperienceInline, EducationInline, SkillInline]
    
    def name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
    name.short_description = 'Name'
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    
    def quick_stats(self, obj):
        exp_count = obj.experiences.count()
        edu_count = obj.educations.count()
        skill_count = obj.skills.count()
        return format_html(
            '<span title="{} experiences, {} education, {} skills">💼 {} | 🎓 {} | ⚡ {}</span>',
            exp_count, edu_count, skill_count, exp_count, edu_count, skill_count
        )
    quick_stats.short_description = 'Stats'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# ========== RECRUITER ADMIN ==========
@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    """Clean and simple Recruiter admin"""
    
    list_display = (
        'name',
        'email',
        'company_link',
        'designation',
        'contact_info',
    )
    
    list_filter = (
        'company',
        'designation',
    )
    
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'company__name',
        'designation',
        'phone_number'
    )
    
    fieldsets = (
        ('👤 Recruiter Info', {
            'fields': ('user', 'designation', 'bio'),
        }),
        ('🏢 Company', {
            'fields': ('company', 'department'),
        }),
        ('📞 Contact', {
            'fields': ('phone_number',),
            'classes': ('wide',)
        }),
    )
    
    autocomplete_fields = ('company',)
    
    def name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
    name.short_description = 'Name'
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    
    def company_link(self, obj):
        if obj.company:
            url = reverse('admin:companies_company_change', args=[obj.company.id])
            return format_html('<a href="{}">{}</a>', url, obj.company.name)
        return "—"
    company_link.short_description = 'Company'
    
    def contact_info(self, obj):
        if obj.phone_number:
            return obj.phone_number
        return "—"
    contact_info.short_description = 'Phone'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'company')


# ========== READ-ONLY ADMINS FOR RELATED MODELS ==========
@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    """Read-only admin for Experience"""
    list_display = ('job_seeker_name', 'title', 'company', 'duration')
    search_fields = ('title', 'company', 'job_seeker__user__email')
    list_per_page = 20
    
    # Make it read-only
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def job_seeker_name(self, obj):
        return obj.job_seeker.user.email
    job_seeker_name.short_description = 'Job Seeker'
    
    def duration(self, obj):
        if obj.currently_working:
            return f"{obj.start_date.year} - Present"
        if obj.end_date:
            return f"{obj.start_date.year} - {obj.end_date.year}"
        return str(obj.start_date.year)
    duration.short_description = 'Duration'


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    """Read-only admin for Education"""
    list_display = ('job_seeker_name', 'degree', 'institution', 'year')
    search_fields = ('degree', 'institution', 'job_seeker__user__email')
    list_per_page = 20
    
    # Make it read-only
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def job_seeker_name(self, obj):
        return obj.job_seeker.user.email
    job_seeker_name.short_description = 'Job Seeker'
    
    def year(self, obj):
        if obj.currently_studying:
            return f"{obj.start_date.year} - Present"
        if obj.end_date:
            return obj.end_date.year
        return obj.start_date.year
    year.short_description = 'Year'


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Read-only admin for Skills"""
    list_display = ('job_seeker_name', 'name', 'proficiency')
    list_filter = ('proficiency',)
    search_fields = ('name', 'job_seeker__user__email')
    list_per_page = 20
    
    # Make it read-only
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def job_seeker_name(self, obj):
        return obj.job_seeker.user.email
    job_seeker_name.short_description = 'Job Seeker'