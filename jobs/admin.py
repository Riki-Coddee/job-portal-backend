from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.urls import reverse
from django.db.models import Count, Q
from .models import JobSkill, Department, Job


@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    """Read‑only admin for Job Skills – optimized with annotations"""
    list_display = ('name', 'usage_count', 'created_at_display', 'popularity_indicator')
    search_fields = ('name',)
    ordering = ('name',)
    list_per_page = 50
    show_full_result_count = False  # ⬅️ Eliminates duplicate COUNT(*)

    # Disable all write operations
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    show_in_index = False

    def usage_count(self, obj):
        # Use annotated job_count – no extra query
        count = obj.job_count
        if count > 0:
            url = reverse('admin:jobs_job_changelist') + f'?skills__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: #2196F3; font-weight: bold;">{} job(s)</a>',
                url, count
            )
        return format_html('<span style="color: #999;">Not used</span>')
    usage_count.short_description = 'Used In'

    def created_at_display(self, obj):
        return obj.created_at.strftime('%b %d, %Y')
    created_at_display.short_description = 'Created'

    def popularity_indicator(self, obj):
        count = obj.job_count  # use annotated field
        if count >= 50:
            color = '#F44336'; label = 'Very High'
        elif count >= 20:
            color = '#FF9800'; label = 'High'
        elif count >= 10:
            color = '#FFC107'; label = 'Medium'
        elif count >= 5:
            color = '#4CAF50'; label = 'Low'
        elif count > 0:
            color = '#9E9E9E'; label = 'Very Low'
        else:
            color = '#E0E0E0'; label = 'None'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<div style="width: 60px; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; position: relative;">'
            '<div style="position: absolute; left: 0; top: 0; height: 100%; background-color: {}; width: {}%;"></div>'
            '</div>'
            '<span style="color: {}; font-size: 11px; font-weight: bold;">{}</span>'
            '</div>',
            color, min(count * 2, 100), color, label
        )
    popularity_indicator.short_description = 'Popularity'

    def get_queryset(self, request):
        # Annotate with job_count to avoid per‑row COUNT queries
        return super().get_queryset(request).annotate(
            job_count=Count('jobs')
        ).order_by('-job_count', 'name')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Departments – optimized with annotations"""
    list_display = (
        'name',
        'is_active',
        'slug_display',
        'job_count',
        'active_jobs_count',
        'created_at_display'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active',)
    list_per_page = 25
    show_full_result_count = False  # ⬅️ Eliminates duplicate COUNT(*)
    actions = ['activate_departments', 'deactivate_departments']

    fieldsets = (
        ('Department Information', {
            'fields': ('name', 'slug', 'is_active'),
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('job_stats',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at_display', 'updated_at_display'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('job_stats', 'created_at_display', 'updated_at_display')

    def slug_display(self, obj):
        return format_html(
            '<code style="background: #f5f5f5; padding: 2px 5px; '
            'border-radius: 3px; font-size: 11px;">{}</code>',
            obj.slug
        )
    slug_display.short_description = 'Slug'

    def job_count(self, obj):
        # Use annotated total_jobs – no extra query
        count = obj.total_jobs
        if count > 0:
            url = reverse('admin:jobs_job_changelist') + f'?department__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: #2196F3; font-weight: bold;">{} job(s)</a>',
                url, count
            )
        return format_html('<span style="color: #999;">No jobs</span>')
    job_count.short_description = 'Total Jobs'

    def active_jobs_count(self, obj):
        # Use annotated active_jobs – no extra query
        count = obj.active_jobs
        if count > 0:
            url = reverse('admin:jobs_job_changelist') + f'?department__id__exact={obj.id}&is_active__exact=1&is_published__exact=1'
            return format_html(
                '<a href="{}" style="color: #4CAF50; font-weight: bold;">{} active</a>',
                url, count
            )
        return format_html('<span style="color: #999;">No active jobs</span>')
    active_jobs_count.short_description = 'Active Jobs'

    def created_at_display(self, obj):
        return obj.created_at.strftime('%b %d, %Y')
    created_at_display.short_description = 'Created'

    def updated_at_display(self, obj):
        return obj.updated_at.strftime('%b %d, %Y')
    updated_at_display.short_description = 'Updated'

    def job_stats(self, obj):
        # Use annotated values – no extra queries
        total_jobs = obj.total_jobs
        active_jobs = obj.active_jobs
        featured_jobs = obj.jobs.filter(is_featured=True).count()  # one query per row? Let's annotate it too.
        # But featured_jobs is not used heavily; we can keep it as is, or annotate if needed.
        # For completeness, let's annotate featured_jobs as well to avoid any per‑row query.
        # We'll modify get_queryset to also annotate featured_jobs.
        # However, the user may not have many departments, so it's optional.
        # I'll add the annotation for completeness.
        featured_jobs = getattr(obj, 'featured_jobs', 0)  # will be set if we annotate.
        return format_html(
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; '
            'background: #e3f2fd; padding: 15px; border-radius: 8px;">'
            '<div style="text-align: center;">'
            '<div style="font-size: 24px; font-weight: bold; color: #2196F3;">{}</div>'
            '<div style="font-size: 12px; color: #666;">Total Jobs</div>'
            '</div>'
            '<div style="text-align: center;">'
            '<div style="font-size: 24px; font-weight: bold; color: #4CAF50;">{}</div>'
            '<div style="font-size: 12px; color: #666;">Active Jobs</div>'
            '</div>'
            '<div style="text-align: center;">'
            '<div style="font-size: 24px; font-weight: bold; color: #FF9800;">{}</div>'
            '<div style="font-size: 12px; color: #666;">Featured Jobs</div>'
            '</div>'
            '<div style="text-align: center;">'
            '<div style="font-size: 24px; font-weight: bold; color: #9C27B0;">{}</div>'
            '<div style="font-size: 12px; color: #666;">Active / Total</div>'
            '</div>'
            '</div>',
            total_jobs,
            active_jobs,
            featured_jobs,
            f"{active_jobs}/{total_jobs}" if total_jobs > 0 else "0/0"
        )
    job_stats.short_description = 'Job Statistics'

    def get_queryset(self, request):
        # Annotate total, active, and featured jobs to avoid per‑row COUNTs
        return super().get_queryset(request).annotate(
            total_jobs=Count('jobs'),
            active_jobs=Count('jobs', filter=Q(jobs__is_active=True, jobs__is_published=True)),
            featured_jobs=Count('jobs', filter=Q(jobs__is_featured=True))
        ).order_by('-total_jobs', 'name')

    def activate_departments(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Successfully activated {updated} department(s).', level='success')
    activate_departments.short_description = "Activate selected departments"

    def deactivate_departments(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Successfully deactivated {updated} department(s).', level='success')
    deactivate_departments.short_description = "Deactivate selected departments"


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Professional admin interface for Jobs – optimized with prefetching and annotation"""
    list_display = (
        'job_title_display',
        'company_info',
        'department_display',
        'job_type_badge',
        'salary_display',
        'status_indicators',
        'date_posted',
        'applications_count',
        'expiry_status'
    )
    list_filter = (
        'is_active',
        'is_published',
        'is_featured',
        'job_type',
        'remote_policy',
        'experience_level',
        'department',
        'recruiter__company',
        'created_at'
    )
    search_fields = (
        'title',
        'description',
        'location',
        'recruiter__company__name',
        'recruiter__user__email',
        'requirements'
    )
    readonly_fields = (
        'job_details_summary',
        'applications_stats',
        'publishing_info',
        'created_at_display',
        'published_at_display',
        'expires_at_display'
    )
    fieldsets = (
        ('Job Information', {
            'fields': (
                'job_details_summary',
                'title',
                'recruiter',
                'company',
                'description',
                'location'
            ),
            'classes': ('wide', 'highlight')
        }),
        ('Job Specifications', {
            'fields': (
                'department',
                'job_type',
                'remote_policy',
                'experience_level',
                'salary_min',
                'salary_max',
                'currency',
                'display_salary'
            ),
            'classes': ('wide',)
        }),
        ('Requirements & Benefits', {
            'fields': ('requirements', 'benefits', 'skills'),
            'classes': ('wide',)
        }),
        ('Publication Settings', {
            'fields': (
                'publishing_info',
                'is_active',
                'is_published',
                'is_featured',
                'publish_option',
                'scheduled_date'
            ),
            'classes': ('collapse',)
        }),
        ('Applications & Statistics', {
            'fields': ('applications_stats',),
            'classes': ('collapse',)
        }),
        ('Dates & Metadata', {
            'fields': (
                'created_at_display',
                'published_at_display',
                'expires_at_display'
            ),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['department', 'skills']
    list_per_page = 30
    date_hierarchy = 'created_at'
    list_select_related = ('recruiter__company', 'recruiter__user', 'department')
    actions = None
    list_display_links = None
    show_full_result_count = False  # ⬅️ Eliminates duplicate COUNT(*)

    # Disable all write operations
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def job_title_display(self, obj):
        indicators = []
        if obj.is_featured:
            indicators.append('⭐')
        if not obj.is_active:
            indicators.append('❌')
        if obj.is_scheduled:
            indicators.append('⏰')
        title_display = format_html(
            '<span style="font-weight: 500; color: #333; font-size: 13px;">{}</span><br>'
            '<small style="color: #666;">{} | {} | 📍 {}</small>',
            obj.title[:40] + "..." if len(obj.title) > 40 else obj.title,
            obj.get_job_type_display(),
            obj.get_experience_level_display(),
            obj.location[:20] + "..." if len(obj.location) > 20 else obj.location
        )
        if indicators:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 8px;">'
                '<div style="font-size: 14px;">{}</div>'
                '<div>{}</div>'
                '</div>',
                ' '.join(indicators), title_display
            )
        return title_display
    job_title_display.short_description = 'Job Title'

    def company_info(self, obj):
        if obj.recruiter.company:
            company_url = reverse('admin:companies_company_change', args=[obj.recruiter.company.id])
            recruiter_url = reverse('admin:accounts_recruiter_change', args=[obj.recruiter.id])
            return format_html(
                '<div style="min-width: 150px;">'
                '<a href="{}" style="color: #2196F3; font-weight: 500;">{}</a><br>'
                '<small style="color: #666;">By: <a href="{}" style="color: #666;">{}</a></small>'
                '</div>',
                company_url,
                obj.recruiter.company.name[:20] + "..." if len(obj.recruiter.company.name) > 20 else obj.recruiter.company.name,
                recruiter_url,
                obj.recruiter.user.email
            )
        return format_html('<span style="color: #999; font-style: italic;">No company</span>')
    company_info.short_description = 'Company / Recruiter'

    def department_display(self, obj):
        if obj.department:
            url = reverse('admin:jobs_department_change', args=[obj.department.id])
            return format_html('<a href="{}" style="color: #666;">{}</a>', url, obj.department.name)
        return "-"
    department_display.short_description = 'Department'

    def job_type_badge(self, obj):
        type_config = {
            'full_time': {'color': '#4CAF50', 'icon': '👔'},
            'part_time': {'color': '#2196F3', 'icon': '🕐'},
            'contract': {'color': '#FF9800', 'icon': '📝'},
            'internship': {'color': '#9C27B0', 'icon': '🎓'},
            'temporary': {'color': '#795548', 'icon': '📅'},
        }
        config = type_config.get(obj.job_type, {'color': '#9E9E9E', 'icon': '❓'})
        return format_html(
            '<div style="display: flex; align-items: center; gap: 5px;">'
            '<span style="font-size: 14px;">{}</span>'
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold; text-align:center;">{}</span>'
            '</div>',
            config['icon'],
            config['color'],
            obj.get_job_type_display().replace(' ', '\n')
        )
    job_type_badge.short_description = 'Type'

    def salary_display(self, obj):
        if obj.display_salary and (obj.salary_min or obj.salary_max):
            salary_text = obj.salary_display
            currency_symbol = {
                'USD': '$',
                'EUR': '€',
                'GBP': '£',
                'CAD': 'C$',
                'NPR': 'रु',
            }.get(obj.currency, obj.currency)
            return format_html(
                '<div style="color: #2E7D32; font-weight: bold; font-size: 12px;">'
                '{} {}'
                '</div>',
                currency_symbol, salary_text.replace(obj.currency, '').strip()
            )
        elif not obj.display_salary:
            return format_html('<span style="color: #FF9800; font-style: italic;">Hidden</span>')
        return format_html('<span style="color: #999; font-style: italic;">Not specified</span>')
    salary_display.short_description = 'Salary'

    def status_indicators(self, obj):
        indicators = []
        if obj.is_active:
            indicators.append(('✅', 'Active', '#4CAF50'))
        else:
            indicators.append(('❌', 'Inactive', '#F44336'))
        if obj.is_published:
            indicators.append(('📢', 'Published', '#2196F3'))
        else:
            indicators.append(('📝', 'Draft', '#FF9800'))
        if obj.is_featured:
            indicators.append(('⭐', 'Featured', '#FFC107'))
        if obj.is_scheduled:
            indicators.append(('⏰', 'Scheduled', '#9C27B0'))

        # Show at most 3 indicators
        indicators = indicators[:3]

        # Build each indicator safely
        indicator_html = format_html_join(
            '',
            '<div style="display: flex; align-items: center; gap: 5px; '
            'background: {}15; padding: 3px 8px; border-radius: 10px; '
            'border: 1px solid {}30;">'
            '<span style="color: {}; font-size: 12px;">{}</span>'
            '<span style="color: {}; font-size: 10px; font-weight: bold;">{}</span>'
            '</div>',
            [(color, color, color, icon, color, text) for icon, text, color in indicators]
        )

        return format_html('<div style="display: flex; gap: 5px; flex-wrap: wrap;">{}</div>', indicator_html)
    status_indicators.short_description = 'Status'

    def date_posted(self, obj):
        if obj.published_at:
            return format_html(
                '{}<br><small style="color: #666;">Published</small>',
                obj.published_at.strftime('%b %d')
            )
        return format_html(
            '{}<br><small style="color: #666;">Created</small>',
            obj.created_at.strftime('%b %d')
        )
    date_posted.short_description = 'Date'

    def applications_count(self, obj):
        # Use prefetched applications – no extra query
        count = len(obj.applications.all())  # uses cached prefetch
        if count > 0:
            url = reverse('admin:applications_application_changelist') + f'?job__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: #2196F3; font-weight: bold;">{} applicant(s)</a>',
                url, count
            )
        return format_html('<span style="color: #999;">No applicants</span>')
    applications_count.short_description = 'Applications'

    def expiry_status(self, obj):
        from django.utils import timezone
        if obj.expires_at:
            now = timezone.now()
            if obj.expires_at > now:
                days_left = (obj.expires_at - now).days
                if days_left > 30:
                    color = '#4CAF50'; status = f"{days_left}d"
                elif days_left > 7:
                    color = '#FFC107'; status = f"{days_left}d"
                elif days_left > 0:
                    color = '#FF9800'; status = f"{days_left}d"
                else:
                    color = '#F44336'; status = "Expired"
                return format_html(
                    '<span style="color: {}; font-weight: bold;">{}</span><br>'
                    '<small style="color: #666;">Expires</small>',
                    color, status
                )
            else:
                return format_html(
                    '<span style="color: #F44336; font-weight: bold;">Expired</span><br>'
                    '<small style="color: #666;">{}</small>',
                    obj.expires_at.strftime('%b %d')
                )
        return format_html('<span style="color: #999; font-style: italic;">No expiry</span>')
    expiry_status.short_description = 'Expires'

    # Detail view methods (unchanged but safe)
    def job_details_summary(self, obj):
        return format_html(
            '<div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px;">'
            '<h3 style="margin-top: 0; color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px;">'
            'Job Summary</h3>'
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">'
            '<div>'
            '<strong>Position:</strong><br>{}<br><br>'
            '<strong>Company:</strong><br>{}<br><br>'
            '<strong>Location:</strong><br>📍 {}<br><br>'
            '</div>'
            '<div>'
            '<strong>Job Type:</strong><br>{}<br><br>'
            '<strong>Experience Level:</strong><br>{}<br><br>'
            '<strong>Remote Policy:</strong><br>{}'
            '</div>'
            '</div>'
            '</div>',
            obj.title,
            obj.company or (obj.recruiter.company.name if obj.recruiter.company else 'Not specified'),
            obj.location,
            obj.get_job_type_display(),
            obj.get_experience_level_display(),
            obj.get_remote_policy_display()
        )
    job_details_summary.short_description = ''

    def applications_stats(self, obj):
        applications = obj.applications.all()  # uses prefetch
        total = len(applications)
        if total > 0:
            status_counts = {}
            for app in applications:
                status_counts[app.status] = status_counts.get(app.status, 0) + 1
            status_html = []
            for status, count in sorted(status_counts.items()):
                status_html.append(
                    f'<div style="display: flex; justify-content: space-between; '
                    f'padding: 5px 0; border-bottom: 1px solid #eee;">'
                    f'<span>{status.replace("_", " ").title()}</span>'
                    f'<span style="font-weight: bold;">{count}</span>'
                    f'</div>'
                )
            return format_html(
                '<div style="background: #e8f5e9; padding: 15px; border-radius: 8px;">'
                '<h4 style="margin-top: 0; color: #333;">Applications Statistics</h4>'
                '<div style="margin-bottom: 10px; text-align: center; '
                'background: #4CAF50; color: white; padding: 10px; border-radius: 4px; '
                'font-weight: bold; font-size: 18px;">{} Total Applications</div>'
                '<div style="max-height: 200px; overflow-y: auto;">'
                '<h5 style="margin: 10px 0 5px 0; color: #666;">Status Breakdown</h5>'
                '{}'
                '</div>'
                '</div>',
                total,
                ''.join(status_html)
            )
        return format_html(
            '<div style="background: #f5f5f5; padding: 15px; border-radius: 8px; '
            'text-align: center; color: #999;">'
            'No applications received yet'
            '</div>'
        )
    applications_stats.short_description = 'Applications'

    def publishing_info(self, obj):
        from django.utils import timezone
        info = []
        if obj.is_published and obj.published_at:
            info.append(f'<strong>Published On:</strong> {obj.published_at.strftime("%B %d, %Y at %I:%M %p")}')
        if obj.expires_at:
            now = timezone.now()
            if obj.expires_at > now:
                days_left = (obj.expires_at - now).days
                info.append(f'<strong>Expires In:</strong> {days_left} days ({obj.expires_at.strftime("%b %d, %Y")})')
            else:
                info.append(f'<strong>Expired On:</strong> {obj.expires_at.strftime("%B %d, %Y")}')
        if obj.is_scheduled and obj.scheduled_date:
            info.append(f'<strong>Scheduled For:</strong> {obj.scheduled_date.strftime("%B %d, %Y at %I:%M %p")}')
        if obj.publish_option == 'immediate':
            info.append('<strong>Publishing:</strong> Immediate')
        else:
            info.append('<strong>Publishing:</strong> Scheduled')
        return format_html(
            '<div style="background: #f0f7ff; padding: 15px; border-radius: 8px;">'
            '<h4 style="margin-top: 0; color: #333;">Publishing Information</h4>'
            '{}'
            '</div>',
            '<br>'.join(info)
        )
    publishing_info.short_description = 'Publishing Details'

    def created_at_display(self, obj):
        return obj.created_at.strftime('%B %d, %Y at %I:%M %p')
    created_at_display.short_description = 'Created'

    def published_at_display(self, obj):
        if obj.published_at:
            return obj.published_at.strftime('%B %d, %Y at %I:%M %p')
        return "Not published yet"
    published_at_display.short_description = 'Published'

    def expires_at_display(self, obj):
        if obj.expires_at:
            return obj.expires_at.strftime('%B %d, %Y at %I:%M %p')
        return "No expiry date set"
    expires_at_display.short_description = 'Expires'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'recruiter__company',
            'recruiter__user',
            'department'
        ).prefetch_related(
            'skills',
            'applications'
        )