from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Q, Exists, OuterRef
from django.utils import timezone
from .models import Application, ApplicationNote, Interview, CandidateTag, CandidateCommunication


# ========== INLINE CLASSES (Read‑only) ==========
class ApplicationNoteInline(admin.TabularInline):
    model = ApplicationNote
    extra = 0
    max_num = 0                     # prevent adding new notes
    fields = ('recruiter', 'note_preview', 'created_at', 'is_private')
    readonly_fields = ('note_preview', 'created_at')
    can_delete = False               # prevent deletion
    classes = ('collapse',)

    def note_preview(self, obj):
        return obj.note[:50] + "..." if len(obj.note) > 50 else obj.note
    note_preview.short_description = 'Note'


class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 0
    max_num = 0
    fields = ('scheduled_date', 'interview_type', 'duration', 'status', 'meeting_link')
    can_delete = False
    classes = ('collapse',)


class CandidateTagInline(admin.TabularInline):
    model = CandidateTag
    extra = 0
    max_num = 0
    fields = ('tag', 'color', 'created_by', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    classes = ('collapse',)


class CandidateCommunicationInline(admin.TabularInline):
    model = CandidateCommunication
    extra = 0
    max_num = 0
    fields = ('communication_type', 'subject', 'content', 'is_outgoing', 'sent_at')
    readonly_fields = ('sent_at',)
    can_delete = False
    classes = ('collapse',)


# ========== APPLICATION ADMIN ==========
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Professional admin interface for Applications – optimized & read‑only"""
    list_display = (
        'application_id',
        'candidate_info',
        'job_info',
        'application_status',
        'match_score_bar',
        'applied_date',
        'last_activity',
        'priority_flags'
    )

    list_filter = (
        'status',
        'is_favorite',
        'is_archived',
        'applied_at',
        'match_score'
    )

    search_fields = (
        'job__title',
        'seeker__user__email',
        'seeker__user__first_name',
        'seeker__user__last_name',
        'cover_letter',
        'recruiter_notes'
    )

    readonly_fields = (
        'application_summary',
        'candidate_details',
        'job_details',
        'application_timeline',
        'match_analysis',
        'interview_history'
    )

    fieldsets = (
        ('Application Overview', {
            'fields': ('application_summary',),
            'classes': ('wide',)
        }),
        ('Application Details', {
            'fields': ('job', 'seeker', 'cover_letter', 'resume_snapshot', 'status')
        }),
        ('Candidate Information', {
            'fields': ('candidate_details',),
            'classes': ('collapse',)
        }),
        ('Job Information', {
            'fields': ('job_details',),
            'classes': ('collapse',)
        }),
        ('Evaluation & Rating', {
            'fields': ('match_score', 'recruiter_rating', 'recruiter_notes', 'skills'),
            'classes': ('collapse',)
        }),
        ('Interview History', {
            'fields': ('interview_history',),
            'classes': ('collapse',)
        }),
        ('Offer Details', {
            'fields': ('offer_made', 'offer_date', 'offer_details'),
            'classes': ('collapse',)
        }),
        ('Activity Tracking', {
            'fields': ('last_viewed', 'last_active', 'messages_count'),
            'classes': ('collapse',)
        }),
        ('Match Analysis', {
            'fields': ('match_analysis',),
            'classes': ('collapse',)
        }),
        ('Application Timeline', {
            'fields': ('application_timeline',),
            'classes': ('collapse',)
        }),
        ('Management', {
            'fields': ('is_favorite', 'is_archived', 'additional_info'),
            'classes': ('collapse',)
        }),
    )

    inlines = [
        ApplicationNoteInline,
        InterviewInline,
        CandidateTagInline,
        CandidateCommunicationInline
    ]

    list_per_page = 25
    date_hierarchy = 'applied_at'
    list_select_related = ('seeker__user', 'job__recruiter__company')  # prefetch in main query
    actions = [
        'mark_as_shortlisted',
        'mark_as_interview',
        'mark_as_rejected',
        'mark_as_hired',
        'toggle_favorite',
        'export_applications_csv'
    ]
    show_full_result_count = False           # eliminate duplicate COUNT(*)

    # Read‑only permissions (view only, but actions can modify)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow view but not direct editing (actions still work)
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    # Helper to safely get status display (handles if get_status_display is a method or property)
    def get_status_display_safe(self, obj):
        value = obj.get_status_display
        if callable(value):
            return value()
        return value

    def application_id(self, obj):
        return format_html('<strong>#{}</strong>', obj.id)
    application_id.short_description = 'ID'

    def candidate_info(self, obj):
        seeker_url = reverse('admin:accounts_jobseeker_change', args=[obj.seeker.id])
        return format_html(
            '<div style="min-width: 180px;">'
            '<a href="{}"><strong>{}</strong></a><br>'
            '<small style="color: #666;">📧 {}</small><br>'
            '<small>📞 {} | 📍 {}</small>'
            '</div>',
            seeker_url,
            f"{obj.seeker.user.first_name} {obj.seeker.user.last_name}",
            obj.seeker.user.email,
            obj.seeker.phone_number or 'No phone',
            obj.seeker.location or 'No location'
        )
    candidate_info.short_description = 'Candidate'
    candidate_info.admin_order_field = 'seeker__user__last_name'

    def job_info(self, obj):
        job_url = reverse('admin:jobs_job_change', args=[obj.job.id])
        company = obj.job.recruiter.company if obj.job.recruiter.company else None
        return format_html(
            '<div style="min-width: 200px;">'
            '<a href="{}">{}</a><br>'
            '<small style="color: #666;">'
            '{} | {}<br>'
            '🏢 {}'
            '</small>'
            '</div>',
            job_url,
            obj.job.title[:30] + "..." if len(obj.job.title) > 30 else obj.job.title,
            obj.job.get_job_type_display(),
            obj.job.get_experience_level_display(),
            company.name[:20] + "..." if company and len(company.name) > 20 else (company.name if company else 'No company')
        )
    job_info.short_description = 'Job'

    def application_status(self, obj):
        status_config = {
            'new': ('#17a2b8', '🆕'),
            'pending': ('#ffc107', '⏳'),
            'reviewed': ('#6c757d', '👁️'),
            'shortlisted': ('#28a745', '⭐'),
            'interview': ('#007bff', '👔'),
            'offer': ('#20c997', '📄'),
            'hired': ('#28a745', '✅'),
            'rejected': ('#dc3545', '❌'),
            'accepted': ('#28a745', '✅'),
            'withdrawn': ('#343a40', '🚪'),
        }
        color, icon = status_config.get(obj.status, ('#6c757d', '❓'))
        # Use safe display helper
        status_display = self.get_status_display_safe(obj)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, status_display
        )
    application_status.short_description = 'Status'

    def match_score_bar(self, obj):
        if obj.match_score >= 80:
            color = '#28a745'
            label = 'Excellent'
        elif obj.match_score >= 60:
            color = '#17a2b8'
            label = 'Good'
        elif obj.match_score >= 40:
            color = '#ffc107'
            label = 'Fair'
        else:
            color = '#dc3545'
            label = 'Poor'
        return format_html(
            '<div style="min-width: 120px;">'
            '<div style="height: 8px; background: #e9ecef; border-radius: 4px; margin-bottom: 3px;">'
            '<div style="height: 8px; background-color: {}; border-radius: 4px; width: {}%"></div>'
            '</div>'
            '<small><span style="color: {};">{}</span> {}%</small>'
            '</div>',
            color, obj.match_score, color, label, obj.match_score
        )
    match_score_bar.short_description = 'Match'

    def applied_date(self, obj):
        delta = timezone.now() - obj.applied_at
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days}d ago"
        return obj.applied_at.strftime('%b %d')
    applied_date.short_description = 'Applied'

    def last_activity(self, obj):
        if obj.last_active:
            delta = timezone.now() - obj.last_active
            if delta.days == 0:
                if delta.seconds < 3600:
                    minutes = delta.seconds // 60
                    return f"{minutes}m ago"
                return f"{delta.seconds // 3600}h ago"
            elif delta.days == 1:
                return "Yesterday"
            elif delta.days < 7:
                return f"{delta.days}d ago"
            return obj.last_active.strftime('%b %d')
        return "Never"
    last_activity.short_description = 'Activity'

    def priority_flags(self, obj):
        flags = []
        if obj.is_favorite:
            flags.append('⭐')
        # Use the annotated field (renamed to avoid conflict with model property)
        if getattr(obj, '_has_scheduled_interview', False):
            flags.append('👔')
        if obj.offer_made:
            flags.append('📄')
        if obj.is_archived:
            flags.append('📁')
        if flags:
            return format_html('<div style="font-size: 16px;">{}</div>', ' '.join(flags))
        return ''
    priority_flags.short_description = 'Flags'

    # Detail view methods
    def application_summary(self, obj):
        if obj.pk:
            rating = '★' * (obj.recruiter_rating or 0) + '☆' * (5 - (obj.recruiter_rating or 0)) if obj.recruiter_rating else 'Not rated'
            return format_html(
                '''
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin-top: 0;">Application Summary</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div><p><strong>Application ID:</strong> #{}</p><p><strong>Applied On:</strong> {}</p><p><strong>Current Status:</strong> {}</p></div>
                        <div><p><strong>Match Score:</strong> {}%</p><p><strong>Recruiter Rating:</strong> {}</p><p><strong>Messages:</strong> {}</p></div>
                    </div>
                </div>
                ''',
                obj.id,
                obj.applied_at.strftime('%B %d, %Y at %I:%M %p'),
                self.application_status(obj),  # this already uses safe display
                obj.match_score,
                rating,
                obj.messages_count
            )
        return format_html('<p>Save the application to see summary</p>')

    def candidate_details(self, obj):
        if obj.pk:
            seeker = obj.seeker
            profile_score = 0
            fields = ['title', 'bio', 'phone_number', 'location', 'resume']
            profile_score = sum(10 for field in fields if getattr(seeker, field) and len(str(getattr(seeker, field)).strip()) > 0)
            if seeker.experiences.exists():
                profile_score += 10
            if seeker.educations.exists():
                profile_score += 10
            if seeker.skills.exists():
                profile_score += 10
            return format_html(
                '<div style="background: #e8f4fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">'
                '<h4 style="margin-top: 0;">Candidate Details</h4>'
                '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">'
                '<div><p><strong>Name:</strong> {} {}</p><p><strong>Email:</strong> {}</p><p><strong>Phone:</strong> {}</p></div>'
                '<div><p><strong>Location:</strong> {}</p><p><strong>Professional Title:</strong> {}</p><p><strong>Profile Score:</strong> {}%</p></div>'
                '</div></div>',
                seeker.user.first_name or '',
                seeker.user.last_name or '',
                seeker.user.email,
                seeker.phone_number or 'Not specified',
                seeker.location or 'Not specified',
                seeker.title or 'Not specified',
                profile_score
            )
        return format_html('<p>Save the application to see candidate details</p>')
    candidate_details.short_description = ''

    def job_details(self, obj):
        if obj.pk:
            job = obj.job
            company = job.recruiter.company if job.recruiter.company else None
            return format_html(
                '<div style="background: #f0f8f0; padding: 15px; border-radius: 8px; margin-bottom: 20px;">'
                '<h4 style="margin-top: 0;">Job Details</h4>'
                '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">'
                '<div><p><strong>Position:</strong> {}</p><p><strong>Company:</strong> {}</p><p><strong>Location:</strong> {}</p></div>'
                '<div><p><strong>Job Type:</strong> {}</p><p><strong>Experience Level:</strong> {}</p><p><strong>Salary:</strong> {}</p></div>'
                '</div></div>',
                job.title,
                company.name if company else 'Not specified',
                job.location,
                job.get_job_type_display(),
                job.get_experience_level_display(),
                job.salary_display if hasattr(job, 'salary_display') else 'Not specified'
            )
        return format_html('<p>Save the application to see job details</p>')
    job_details.short_description = ''

    def application_timeline(self, obj):
        if obj.pk:
            events = [('📝', 'Applied', obj.applied_at)]
            if obj.last_viewed:
                events.append(('👁️', 'Last Viewed', obj.last_viewed))
            if obj.last_message_at:
                events.append(('💬', 'Last Message', obj.last_message_at))
            if obj.last_active:
                events.append(('🔄', 'Last Active', obj.last_active))
            timeline_divs = []
            for icon, label, timestamp in sorted(events, key=lambda x: x[2], reverse=True):
                timeline_divs.append(
                    f'<div style="display: flex; align-items: start; margin-bottom: 10px;">'
                    f'<div style="font-size: 16px; margin-right: 10px;">{icon}</div>'
                    f'<div><div>{label}</div><small style="color: #666;">{timestamp.strftime("%b %d, %Y %H:%M")}</small></div>'
                    f'</div>'
                )
            return format_html(
                '<div style="background: #fff8e1; padding: 15px; border-radius: 8px; margin-bottom: 20px;">'
                '<h4 style="margin-top: 0;">Application Timeline</h4>'
                '{}</div>',
                format_html(''.join(timeline_divs))
            )
        return format_html('<p>Save the application to see timeline</p>')
    application_timeline.short_description = ''

    def match_analysis(self, obj):
        if obj.pk:
            analysis_items = []
            if obj.match_score >= 80:
                analysis_items.append('<div style="margin-bottom: 8px;"><span style="font-size: 16px;">✅</span> Excellent match with job requirements</div>')
            elif obj.match_score >= 60:
                analysis_items.append('<div style="margin-bottom: 8px;"><span style="font-size: 16px;">⚠️</span> Good match, minor gaps identified</div>')
            else:
                analysis_items.append('<div style="margin-bottom: 8px;"><span style="font-size: 16px;">❌</span> Poor match with job requirements</div>')
            if obj.recruiter_rating and obj.recruiter_rating >= 4:
                analysis_items.append('<div style="margin-bottom: 8px;"><span style="font-size: 16px;">⭐</span> Highly rated by recruiter</div>')
            if obj.is_favorite:
                analysis_items.append('<div style="margin-bottom: 8px;"><span style="font-size: 16px;">❤️</span> Marked as favorite</div>')
            if analysis_items:
                return format_html(
                    '<div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px;">'
                    '<h4 style="margin-top: 0;">Match Analysis</h4>{}</div>',
                    format_html(''.join(analysis_items))
                )
            return format_html('<p style="color: #666;">No analysis available</p>')
        return format_html('<p>Save the application to see match analysis</p>')
    match_analysis.short_description = ''

    def interview_history(self, obj):
        if obj.pk:
            interviews = obj.interviews.all()
            if interviews:
                history_divs = []
                for interview in interviews[:5]:
                    status_color = {
                        'scheduled': '#17a2b8',
                        'completed': '#28a745',
                        'cancelled': '#dc3545',
                        'rescheduled': '#ffc107',
                    }.get(interview.status, '#6c757d')
                    history_divs.append(
                        f'<div style="background: white; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; margin-bottom: 10px;">'
                        f'<h6 style="margin-top: 0; margin-bottom: 5px;">{interview.scheduled_date.strftime("%b %d, %Y %I:%M %p")}</h6>'
                        f'<p style="margin-bottom: 5px;">'
                        f'<span style="background-color: {status_color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">{interview.get_status_display()}</span>'
                        f'<span style="background-color: #6c757d; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px; margin-left: 5px;">{interview.get_interview_type_display()}</span>'
                        f'</p></div>'
                    )
                return format_html(
                    '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">'
                    '<h4 style="margin-top: 0;">Interview History</h4>{}</div>',
                    format_html(''.join(history_divs))
                )
            return format_html('<p style="color: #666;">No interviews scheduled</p>')
        return format_html('<p>Save the application to see interview history</p>')
    interview_history.short_description = ''

    # Actions
    @admin.action(description="Mark as shortlisted")
    def mark_as_shortlisted(self, request, queryset):
        updated = queryset.update(status='shortlisted')
        self.message_user(request, f'{updated} application(s) marked as shortlisted.')

    @admin.action(description="Mark for interview")
    def mark_as_interview(self, request, queryset):
        updated = queryset.update(status='interview')
        self.message_user(request, f'{updated} application(s) marked for interview.')

    @admin.action(description="Mark as rejected")
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} application(s) rejected.')

    @admin.action(description="Mark as hired")
    def mark_as_hired(self, request, queryset):
        for app in queryset:
            app.status = 'hired'
            app.hired_date = timezone.now()
            app.save()
        self.message_user(request, f'{queryset.count()} candidate(s) hired.')

    @admin.action(description="Toggle favorite")
    def toggle_favorite(self, request, queryset):
        for app in queryset:
            app.is_favorite = not app.is_favorite
            app.save()
        self.message_user(request, f'{queryset.count()} application(s) favorite status toggled.')

    @admin.action(description="Export to CSV")
    def export_applications_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Candidate', 'Email', 'Job Title', 'Company', 'Status', 'Match Score', 'Applied Date', 'Rating'])
        for app in queryset:
            # Use safe display helper
            status_display = self.get_status_display_safe(app)
            writer.writerow([
                app.id,
                f"{app.seeker.user.first_name} {app.seeker.user.last_name}",
                app.seeker.user.email,
                app.job.title,
                app.job.recruiter.company.name if app.job.recruiter.company else '',
                status_display,
                app.match_score,
                app.applied_at.strftime('%Y-%m-%d'),
                app.recruiter_rating or ''
            ])
        return response

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate with scheduled interview existence (renamed to avoid conflict with model property)
        qs = qs.annotate(
            _has_scheduled_interview=Exists(
                Interview.objects.filter(
                    application=OuterRef('pk'),
                    status='scheduled'
                )
            )
        )
        return qs.select_related(
            'seeker__user',
            'job__recruiter__company',
            'job__recruiter__user'
        ).prefetch_related(
            'interviews',
            'notes',
            'tags',
            'communications'
        )


# ========== APPLICATION NOTE ADMIN ==========
@admin.register(ApplicationNote)
class ApplicationNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'application_link', 'recruiter_link', 'note_preview', 'privacy_badge', 'created_at')
    list_filter = ('is_private', 'created_at', 'recruiter')
    search_fields = ('note', 'application__seeker__user__email', 'recruiter__user__email')
    readonly_fields = ('application_details', 'recruiter_details', 'created_at_display')
    fieldsets = (
        ('Note Details', {'fields': ('application', 'recruiter', 'note', 'is_private')}),
        ('Application Details', {'fields': ('application_details',), 'classes': ('collapse',)}),
        ('Recruiter Details', {'fields': ('recruiter_details',), 'classes': ('collapse',)}),
        ('Metadata', {'fields': ('created_at_display',), 'classes': ('collapse',)}),
    )
    list_per_page = 25
    date_hierarchy = 'created_at'
    show_full_result_count = False

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    def application_link(self, obj):
        url = reverse('admin:applications_application_change', args=[obj.application.id])
        return format_html('<a href="{}">#{}</a><br><small style="color: #666;">{}</small>',
                           url, obj.application.id,
                           obj.application.job.title[:30] + "..." if len(obj.application.job.title) > 30 else obj.application.job.title)
    application_link.short_description = 'Application'

    def recruiter_link(self, obj):
        url = reverse('admin:accounts_recruiter_change', args=[obj.recruiter.id])
        return format_html('<a href="{}">{}</a>', url, obj.recruiter.user.email)
    recruiter_link.short_description = 'Recruiter'

    def note_preview(self, obj):
        preview = obj.note[:60] + "..." if len(obj.note) > 60 else obj.note
        return format_html('<div style="max-width: 200px;">{}</div>', preview)
    note_preview.short_description = 'Note'

    def privacy_badge(self, obj):
        if obj.is_private:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">Private</span>')
        return format_html('<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">Public</span>')
    privacy_badge.short_description = 'Privacy'

    def application_details(self, obj):
        if obj.pk:
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">'
                '<h4>Application Details</h4>'
                '<p><strong>ID:</strong> #{}</p>'
                '<p><strong>Candidate:</strong> {} {}</p>'
                '<p><strong>Job:</strong> {}</p></div>',
                obj.application.id,
                obj.application.seeker.user.first_name or '',
                obj.application.seeker.user.last_name or '',
                obj.application.job.title
            )
        return ''
    application_details.short_description = ''

    def recruiter_details(self, obj):
        if obj.pk:
            return format_html(
                '<div style="background: #e8f4fd; padding: 15px; border-radius: 8px;">'
                '<h4>Recruiter Details</h4>'
                '<p><strong>Name:</strong> {} {}</p>'
                '<p><strong>Email:</strong> {}</p>'
                '<p><strong>Company:</strong> {}</p></div>',
                obj.recruiter.user.first_name or '',
                obj.recruiter.user.last_name or '',
                obj.recruiter.user.email,
                obj.recruiter.company.name if obj.recruiter.company else 'No company'
            )
        return ''
    recruiter_details.short_description = ''

    def created_at_display(self, obj):
        if obj.pk:
            return obj.created_at.strftime('%B %d, %Y at %I:%M %p')
        return ''
    created_at_display.short_description = 'Created'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'application__job',
            'application__seeker__user',
            'recruiter__user',
            'recruiter__company'
        )


# ========== INTERVIEW ADMIN ==========
@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate_info', 'scheduled_date', 'interview_type_badge', 'duration', 'status_badge', 'has_feedback')
    list_filter = ('status', 'interview_type', 'scheduled_date')
    search_fields = ('application__seeker__user__email', 'application__job__title', 'feedback', 'location')
    readonly_fields = ('application_details', 'timing_info', 'scheduler_details')
    fieldsets = (
        ('Interview Details', {'fields': ('application', 'scheduled_date', 'duration', 'interview_type', 'status')}),
        ('Logistics', {'fields': ('meeting_link', 'location'), 'classes': ('collapse',)}),
        ('Feedback', {'fields': ('feedback', 'rating'), 'classes': ('collapse',)}),
        ('Scheduler', {'fields': ('scheduled_by',), 'classes': ('collapse',)}),
        ('Application Details', {'fields': ('application_details',), 'classes': ('collapse',)}),
        ('Timing Information', {'fields': ('timing_info',), 'classes': ('collapse',)}),
        ('Scheduler Details', {'fields': ('scheduler_details',), 'classes': ('collapse',)}),
    )
    list_per_page = 25
    date_hierarchy = 'scheduled_date'
    show_full_result_count = False

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    def candidate_info(self, obj):
        app = obj.application
        return format_html(
            '<div style="min-width: 180px;">'
            '<strong>{} {}</strong><br>'
            '<small style="color: #666;">📧 {}</small><br>'
            '<small>For: {}</small></div>',
            app.seeker.user.first_name or '',
            app.seeker.user.last_name or '',
            app.seeker.user.email,
            app.job.title[:30] + "..." if len(app.job.title) > 30 else app.job.title
        )
    candidate_info.short_description = 'Candidate'

    def interview_type_badge(self, obj):
        type_colors = {'phone': '#17a2b8', 'video': '#007bff', 'onsite': '#ffc107', 'technical': '#dc3545'}
        color = type_colors.get(obj.interview_type, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
                           color, obj.get_interview_type_display())
    interview_type_badge.short_description = 'Type'

    def status_badge(self, obj):
        status_colors = {'scheduled': '#17a2b8', 'completed': '#28a745', 'cancelled': '#dc3545', 'rescheduled': '#ffc107'}
        color = status_colors.get(obj.status, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
                           color, obj.get_status_display())
    status_badge.short_description = 'Status'

    def has_feedback(self, obj):
        if obj.feedback:
            return format_html('<span style="color: #28a745;">✓</span>')
        return format_html('<span style="color: #666;">✗</span>')
    has_feedback.short_description = 'Feedback'

    def application_details(self, obj):
        if obj.pk:
            app = obj.application
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">'
                '<h4>Application Details</h4>'
                '<p><strong>Candidate:</strong> {} {}</p>'
                '<p><strong>Email:</strong> {}</p>'
                '<p><strong>Job:</strong> {}</p>'
                '<p><strong>Status:</strong> {}</p></div>',
                app.seeker.user.first_name or '',
                app.seeker.user.last_name or '',
                app.seeker.user.email,
                app.job.title,
                app.get_status_display()
            )
        return ''
    application_details.short_description = ''

    def timing_info(self, obj):
        if obj.pk:
            now = timezone.now()
            if obj.scheduled_date > now:
                time_until = obj.scheduled_date - now
                status = "Upcoming"
                time_text = f"in {time_until.days} days, {time_until.seconds // 3600} hours"
            else:
                time_since = now - obj.scheduled_date
                status = "Past"
                time_text = f"{time_since.days} days, {time_since.seconds // 3600} hours ago"
            return format_html(
                '<div style="background: #fff8e1; padding: 15px; border-radius: 8px;">'
                '<h4>Timing Information</h4>'
                '<p><strong>Scheduled:</strong> {}</p>'
                '<p><strong>Ends:</strong> {}</p>'
                '<p><strong>Status:</strong> {} ({})</p></div>',
                obj.scheduled_date.strftime('%B %d, %Y at %I:%M %p'),
                obj.interview_end_time.strftime('%I:%M %p'),
                status, time_text
            )
        return ''
    timing_info.short_description = ''

    def scheduler_details(self, obj):
        if obj.pk and obj.scheduled_by:
            return format_html(
                '<div style="background: #e8f4fd; padding: 15px; border-radius: 8px;">'
                '<h4>Scheduled By</h4>'
                '<p><strong>Name:</strong> {} {}</p>'
                '<p><strong>Email:</strong> {}</p>'
                '<p><strong>Company:</strong> {}</p>'
                '<p><strong>Designation:</strong> {}</p></div>',
                obj.scheduled_by.user.first_name or '',
                obj.scheduled_by.user.last_name or '',
                obj.scheduled_by.user.email,
                obj.scheduled_by.company.name if obj.scheduled_by.company else 'No company',
                obj.scheduled_by.designation or 'Recruiter'
            )
        return format_html('<p style="color: #666;">Not specified</p>')
    scheduler_details.short_description = ''

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'application__seeker__user',
            'application__job',
            'scheduled_by__user',
            'scheduled_by__company'
        )


# ========== CANDIDATE TAG ADMIN ==========
@admin.register(CandidateTag)
class CandidateTagAdmin(admin.ModelAdmin):
    list_display = ('tag_display', 'application_link', 'candidate_info', 'created_by_link', 'created_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('tag', 'application__seeker__user__email', 'created_by__user__email')
    readonly_fields = ('application_details', 'creator_details', 'created_at_display')
    fieldsets = (
        ('Tag Information', {'fields': ('application', 'tag', 'color', 'created_by')}),
        ('Application Details', {'fields': ('application_details',), 'classes': ('collapse',)}),
        ('Creator Details', {'fields': ('creator_details',), 'classes': ('collapse',)}),
        ('Metadata', {'fields': ('created_at_display',), 'classes': ('collapse',)}),
    )
    list_per_page = 25
    date_hierarchy = 'created_at'
    show_full_result_count = False

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    def tag_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 12px; font-size: 12px;">{}</span>',
            obj.color, obj.tag
        )
    tag_display.short_description = 'Tag'

    def application_link(self, obj):
        url = reverse('admin:applications_application_change', args=[obj.application.id])
        return format_html('<a href="{}">#{}</a>', url, obj.application.id)
    application_link.short_description = 'Application'

    def candidate_info(self, obj):
        seeker = obj.application.seeker
        return format_html('{} {}<br><small style="color: #666;">📧 {}</small>',
                           seeker.user.first_name or '', seeker.user.last_name or '', seeker.user.email)
    candidate_info.short_description = 'Candidate'

    def created_by_link(self, obj):
        url = reverse('admin:accounts_recruiter_change', args=[obj.created_by.id])
        return format_html('<a href="{}">{}</a>', url, obj.created_by.user.email)
    created_by_link.short_description = 'Created By'

    def application_details(self, obj):
        if obj.pk:
            app = obj.application
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">'
                '<h4>Application Details</h4>'
                '<p><strong>ID:</strong> #{}</p>'
                '<p><strong>Candidate:</strong> {} {}</p>'
                '<p><strong>Job:</strong> {}</p>'
                '<p><strong>Status:</strong> {}</p></div>',
                app.id,
                app.seeker.user.first_name or '',
                app.seeker.user.last_name or '',
                app.job.title,
                app.get_status_display()
            )
        return ''
    application_details.short_description = ''

    def creator_details(self, obj):
        if obj.pk:
            return format_html(
                '<div style="background: #e8f4fd; padding: 15px; border-radius: 8px;">'
                '<h4>Created By</h4>'
                '<p><strong>Recruiter:</strong> {} {}</p>'
                '<p><strong>Email:</strong> {}</p>'
                '<p><strong>Company:</strong> {}</p></div>',
                obj.created_by.user.first_name or '',
                obj.created_by.user.last_name or '',
                obj.created_by.user.email,
                obj.created_by.company.name if obj.created_by.company else 'No company'
            )
        return ''
    creator_details.short_description = ''

    def created_at_display(self, obj):
        if obj.pk:
            return obj.created_at.strftime('%B %d, %Y at %I:%M %p')
        return ''
    created_at_display.short_description = 'Created'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'application__seeker__user',
            'application__job',
            'created_by__user',
            'created_by__company'
        )


# ========== CANDIDATE COMMUNICATION ADMIN ==========
@admin.register(CandidateCommunication)
class CandidateCommunicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'application_link', 'type_badge', 'subject_preview', 'direction_badge', 'sent_at', 'recruiter_link')
    list_filter = ('communication_type', 'is_outgoing', 'sent_at', 'recruiter')
    search_fields = ('subject', 'content', 'application__seeker__user__email', 'recruiter__user__email')
    readonly_fields = ('application_details', 'communication_content', 'recruiter_details', 'sent_at_display')
    fieldsets = (
        ('Communication Details', {'fields': ('application', 'recruiter', 'communication_type', 'subject', 'content', 'is_outgoing', 'attachments')}),
        ('Application Details', {'fields': ('application_details',), 'classes': ('collapse',)}),
        ('Communication Content', {'fields': ('communication_content',), 'classes': ('collapse',)}),
        ('Recruiter Details', {'fields': ('recruiter_details',), 'classes': ('collapse',)}),
        ('Metadata', {'fields': ('sent_at_display',), 'classes': ('collapse',)}),
    )
    list_per_page = 25
    date_hierarchy = 'sent_at'
    show_full_result_count = False

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    def application_link(self, obj):
        url = reverse('admin:applications_application_change', args=[obj.application.id])
        return format_html(
            '<a href="{}">#{}</a><br><small style="color: #666;">{}</small>',
            url, obj.application.id,
            obj.application.job.title[:30] + "..." if len(obj.application.job.title) > 30 else obj.application.job.title
        )
    application_link.short_description = 'Application'

    def type_badge(self, obj):
        type_colors = {'email': '#007bff', 'call': '#17a2b8', 'message': '#28a745', 'interview': '#ffc107', 'offer': '#dc3545'}
        color = type_colors.get(obj.communication_type, '#6c757d')
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
                           color, obj.get_communication_type_display())
    type_badge.short_description = 'Type'

    def subject_preview(self, obj):
        text = obj.subject or obj.content
        preview = text[:50] + "..." if text and len(text) > 50 else (text or "No content")
        return format_html('<div style="max-width: 200px;">{}</div>', preview)
    subject_preview.short_description = 'Subject/Content'

    def direction_badge(self, obj):
        if obj.is_outgoing:
            return format_html('<span style="background-color: #007bff; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">→ Outgoing</span>')
        return format_html('<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">← Incoming</span>')
    direction_badge.short_description = 'Direction'

    def recruiter_link(self, obj):
        url = reverse('admin:accounts_recruiter_change', args=[obj.recruiter.id])
        return format_html('<a href="{}">{}</a>', url, obj.recruiter.user.email)
    recruiter_link.short_description = 'Recruiter'

    def application_details(self, obj):
        if obj.pk:
            app = obj.application
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">'
                '<h4>Application Details</h4>'
                '<p><strong>ID:</strong> #{}</p>'
                '<p><strong>Candidate:</strong> {} {}</p>'
                '<p><strong>Email:</strong> {}</p>'
                '<p><strong>Job:</strong> {}</p></div>',
                app.id,
                app.seeker.user.first_name or '',
                app.seeker.user.last_name or '',
                app.seeker.user.email,
                app.job.title
            )
        return ''
    application_details.short_description = ''

    def communication_content(self, obj):
        if obj.pk:
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">'
                '<h4>Message Content</h4>'
                '<div style="background: white; padding: 15px; border-radius: 5px; border: 1px solid #dee2e6; white-space: pre-wrap;">{}</div>'
                '</div>',
                obj.content
            )
        return ''
    communication_content.short_description = ''

    def recruiter_details(self, obj):
        if obj.pk:
            return format_html(
                '<div style="background: #e8f4fd; padding: 15px; border-radius: 8px;">'
                '<h4>Recruiter Details</h4>'
                '<p><strong>Name:</strong> {} {}</p>'
                '<p><strong>Email:</strong> {}</p>'
                '<p><strong>Company:</strong> {}</p>'
                '<p><strong>Designation:</strong> {}</p></div>',
                obj.recruiter.user.first_name or '',
                obj.recruiter.user.last_name or '',
                obj.recruiter.user.email,
                obj.recruiter.company.name if obj.recruiter.company else 'No company',
                obj.recruiter.designation or 'Recruiter'
            )
        return ''
    recruiter_details.short_description = ''

    def sent_at_display(self, obj):
        if obj.pk:
            return obj.sent_at.strftime('%B %d, %Y at %I:%M %p')
        return ''
    sent_at_display.short_description = 'Sent'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'application__seeker__user',
            'application__job',
            'recruiter__user',
            'recruiter__company'
        )