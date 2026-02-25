# contact/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import FAQ, ContactMessage

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['question', 'answer']
    ordering = ['order']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'category', 'subject_preview', 'is_resolved', 'created_at']
    list_filter = ['category', 'is_resolved', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['ip_address', 'user_agent', 'created_at', 'responded_at']
    fieldsets = (
        ('Sender Information', {
            'fields': ('name', 'email', 'ip_address', 'user_agent')
        }),
        ('Message Details', {
            'fields': ('category', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('is_resolved', 'responded_at', 'admin_notes')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_resolved', 'mark_as_unresolved']
    
    def subject_preview(self, obj):
        return obj.subject[:50] + "..." if len(obj.subject) > 50 else obj.subject
    subject_preview.short_description = 'Subject'
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, responded_at=timezone.now())
        self.message_user(request, f"{queryset.count()} messages marked as resolved.")
    mark_as_resolved.short_description = "Mark selected as resolved"
    
    def mark_as_unresolved(self, request, queryset):
        queryset.update(is_resolved=False, responded_at=None)
        self.message_user(request, f"{queryset.count()} messages marked as unresolved.")
    mark_as_unresolved.short_description = "Mark selected as unresolved"