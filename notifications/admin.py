from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Professional admin interface for Notifications"""
    list_display = (
        'notification_id',
        'user_info',
        'notification_type_badge',
        'title_preview',
        'priority_badge',
        'read_status',
        'created_ago',
        'related_object'
    )
    
    list_filter = (
        'is_read',
        'notification_type',
        'priority',
        'created_at'
    )
    
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'title',
        'message'
    )
    
    readonly_fields = (
        'notification_details',
        'user_details',
        'related_object_info',
        'created_at_display',
        'read_at_display'
    )
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('notification_details',),
            'classes': ('wide', 'info-box')
        }),
        ('Content', {
            'fields': ('user_details', 'title', 'message', 'action_url'),
            'classes': ('wide',)
        }),
        ('Type & Priority', {
            'fields': ('notification_type', 'priority'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read',),
            'classes': ('collapse',)
        }),
        ('Related Objects', {
            'fields': ('related_object_info',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at_display', 'read_at_display'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread', 'export_notifications_csv']
    
    def notification_id(self, obj):
        """Display notification ID"""
        return format_html(
            '<strong>#{}</strong>',
            obj.id
        )
    notification_id.short_description = 'ID'
    
    def user_info(self, obj):
        """Display user information"""
        url = reverse('admin:accounts_customuser_change', args=[obj.user.id])
        
        # Determine user role for appropriate link
        if hasattr(obj.user, 'seeker_profile'):
            profile_url = reverse('admin:accounts_jobseeker_change', args=[obj.user.seeker_profile.id])
        elif hasattr(obj.user, 'recruiter'):
            profile_url = reverse('admin:accounts_recruiter_change', args=[obj.user.recruiter.id])
        else:
            profile_url = url
        
        return format_html(
            '<div style="min-width: 180px;">'
            '<a href="{}"><strong>{}</strong></a><br>'
            '<small class="text-muted">📧 {}</small><br>'
            '<small><a href="{}">View Profile</a></small>'
            '</div>',
            url,
            f"{obj.user.first_name} {obj.user.last_name}" if obj.user.first_name or obj.user.last_name else obj.user.email,
            obj.user.email,
            profile_url
        )
    user_info.short_description = 'User'
    
    def notification_type_badge(self, obj):
        """Display notification type with badge"""
        type_config = {
            'application_update': ('info', '📄'),
            'interview_scheduled': ('primary', '👔'),
            'interview_reminder': ('warning', '⏰'),
            'new_message': ('success', '💬'),
            'job_recommendation': ('danger', '⭐'),
            'application_status_change': ('secondary', '🔄'),
            'offer_extended': ('success', '🏆'),
            'system_alert': ('dark', '⚠️'),
        }
        
        color, icon = type_config.get(obj.notification_type, ('secondary', '🔔'))
        
        return format_html(
            '<span class="badge bg-{}" style="font-size: 11px;">{} {}</span>',
            color, icon, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'
    
    def title_preview(self, obj):
        """Display title preview"""
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title'
    
    def priority_badge(self, obj):
        """Display priority badge"""
        priority_colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
        }
        color = priority_colors.get(obj.priority, 'secondary')
        
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_priority_display().upper()
        )
    priority_badge.short_description = 'Priority'
    
    def read_status(self, obj):
        """Display read status"""
        if obj.is_read:
            return format_html(
                '<span class="badge bg-success">Read</span><br>'
                '<small class="text-muted">{}</small>',
                obj.read_at.strftime('%b %d') if obj.read_at else ''
            )
        return format_html(
            '<span class="badge bg-danger">Unread</span>'
        )
    read_status.short_description = 'Status'
    
    def created_ago(self, obj):
        """Display time ago"""
        return obj.time_ago
    created_ago.short_description = 'Created'
    
    def related_object(self, obj):
        """Display related object"""
        if obj.application:
            url = reverse('admin:applications_application_change', args=[obj.application.id])
            return format_html(
                '<a href="{}">Application #{}</a>',
                url, obj.application.id
            )
        elif obj.interview:
            url = reverse('admin:applications_interview_change', args=[obj.interview.id])
            return format_html(
                '<a href="{}">Interview</a>',
                url
            )
        elif obj.job:
            url = reverse('admin:jobs_job_change', args=[obj.job.id])
            return format_html(
                '<a href="{}">Job</a>',
                url
            )
        return format_html('<span class="text-muted">-</span>')
    related_object.short_description = 'Related To'
    
    # Detail view methods
    def notification_details(self, obj):
        """Display notification details"""
        return format_html(
            '<div class="info-box">'
            '<h3>Notification Details</h3>'
            '<div class="row">'
            '<div class="col-md-6">'
            '<p><strong>ID:</strong> #{}</p>'
            '<p><strong>Type:</strong> {}</p>'
            '<p><strong>Priority:</strong> {}</p>'
            '</div>'
            '<div class="col-md-6">'
            '<p><strong>Created:</strong> {}</p>'
            '<p><strong>Status:</strong> {}</p>'
            '<p><strong>Read At:</strong> {}</p>'
            '</div>'
            '</div>'
            '</div>',
            obj.id,
            obj.get_notification_type_display(),
            obj.get_priority_display(),
            obj.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'Read' if obj.is_read else 'Unread',
            obj.read_at.strftime('%B %d, %Y at %I:%M %p') if obj.read_at else 'Not read'
        )
    notification_details.short_description = ''
    
    def user_details(self, obj):
        """Display user details"""
        return format_html(
            '<div class="info-box">'
            '<h4>User Information</h4>'
            '<p><strong>Name:</strong> {} {}</p>'
            '<p><strong>Email:</strong> {}</p>'
            '<p><strong>Role:</strong> {}</p>'
            '</div>',
            obj.user.first_name or '',
            obj.user.last_name or '',
            obj.user.email,
            obj.user.get_role_display()
        )
    user_details.short_description = ''
    
    def related_object_info(self, obj):
        """Display related object information"""
        info_parts = []
        
        if obj.application:
            url = reverse('admin:applications_application_change', args=[obj.application.id])
            info_parts.append(f'<p><strong>Application:</strong> <a href="{url}">#{obj.application.id}</a></p>')
            info_parts.append(f'<p><strong>Candidate:</strong> {obj.application.seeker.user.get_full_name() or obj.application.seeker.user.email}</p>')
            info_parts.append(f'<p><strong>Job:</strong> {obj.application.job.title}</p>')
        
        if obj.interview:
            url = reverse('admin:applications_interview_change', args=[obj.interview.id])
            info_parts.append(f'<p><strong>Interview:</strong> <a href="{url}">Scheduled for {obj.interview.scheduled_date.strftime("%B %d, %Y")}</a></p>')
        
        if obj.job:
            url = reverse('admin:jobs_job_change', args=[obj.job.id])
            info_parts.append(f'<p><strong>Job:</strong> <a href="{url}">{obj.job.title}</a></p>')
        
        if info_parts:
            return format_html(
                '<div class="info-box">'
                '<h4>Related Information</h4>'
                '{}'
                '</div>',
                ''.join(info_parts)
            )
        return format_html('<p class="text-muted">No related objects</p>')
    related_object_info.short_description = ''
    
    def created_at_display(self, obj):
        """Display creation date"""
        return obj.created_at.strftime('%B %d, %Y at %I:%M %p')
    created_at_display.short_description = 'Created'
    
    def read_at_display(self, obj):
        """Display read date"""
        if obj.read_at:
            return obj.read_at.strftime('%B %d, %Y at %I:%M %p')
        return 'Not read yet'
    read_at_display.short_description = 'Read At'
    
    @admin.action(description="Mark as read")
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read"""
        from django.utils import timezone
        
        for notification in queryset:
            notification.mark_as_read()
        
        self.message_user(request, f'{queryset.count()} notification(s) marked as read.')
    
    @admin.action(description="Mark as unread")
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread"""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notification(s) marked as unread.')
    
    @admin.action(description="Export to CSV")
    def export_notifications_csv(self, request, queryset):
        """Export notifications to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="notifications_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User Email', 'Type', 'Title', 'Priority', 'Read Status',
            'Created Date', 'Related Object'
        ])
        
        for notification in queryset:
            related_obj = ''
            if notification.application:
                related_obj = f'Application #{notification.application.id}'
            elif notification.interview:
                related_obj = f'Interview #{notification.interview.id}'
            elif notification.job:
                related_obj = f'Job: {notification.job.title}'
            
            writer.writerow([
                notification.id,
                notification.user.email,
                notification.get_notification_type_display(),
                notification.title,
                notification.get_priority_display(),
                'Read' if notification.is_read else 'Unread',
                notification.created_at.strftime('%Y-%m-%d %H:%M'),
                related_obj
            ])
        
        return response
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'user',
            'application__seeker__user',
            'application__job',
            'interview',
            'job'
        )