from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import Conversation, Message, MessageAttachment, ConversationSettings


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    # Show all fields in a compact, read‑only way
    fields = ('sender_link', 'receiver_link', 'content_preview', 'message_type', 'status', 'created_at')
    readonly_fields = ('sender_link', 'receiver_link', 'content_preview', 'message_type', 'status', 'created_at')
    can_delete = False  # Prevent inline deletion (use separate admin for moderation)

    def sender_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.get_full_name())
    sender_link.short_description = 'Sender'

    def receiver_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.receiver.id])
        return format_html('<a href="{}">{}</a>', url, obj.receiver.get_full_name())
    receiver_link.short_description = 'Receiver'

    def content_preview(self, obj):
        return obj.content[:60] + "..." if len(obj.content) > 60 else obj.content
    content_preview.short_description = "Content"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'recruiter_link',
        'job_seeker_link',
        'job_link',
        'last_message_at',
        'unread_display',
        'is_archived',
        'is_pinned'
    )
    list_filter = (
        'is_archived',
        'is_pinned',
        'is_muted',
        'created_at',
        'last_message_at',
        'job__title'
    )
    search_fields = (
        'recruiter__user__email',
        'recruiter__user__first_name',
        'recruiter__user__last_name',
        'job_seeker__user__email',
        'job_seeker__user__first_name',
        'job_seeker__user__last_name',
        'job__title',
        'subject'
    )
    readonly_fields = (
        'recruiter',
        'job_seeker',
        'job',
        'application',
        'created_at',
        'updated_at',
        'last_message_at'
    )
    fieldsets = (
        ('Participants', {
            'fields': ('recruiter', 'job_seeker', 'job', 'application')
        }),
        ('Conversation Info', {
            'fields': ('subject', 'is_archived', 'is_pinned', 'is_muted')
        }),
        ('Unread Counts', {
            'fields': ('unread_by_recruiter', 'unread_by_job_seeker'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_message_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [MessageInline]
    actions = ['archive_conversations', 'unarchive_conversations']

    def recruiter_link(self, obj):
        url = reverse('admin:accounts_recruiter_change', args=[obj.recruiter.id])
        return format_html('<a href="{}">{}</a>', url, obj.recruiter.user.get_full_name())
    recruiter_link.short_description = "Recruiter"

    def job_seeker_link(self, obj):
        url = reverse('admin:accounts_jobseeker_change', args=[obj.job_seeker.id])
        return format_html('<a href="{}">{}</a>', url, obj.job_seeker.user.get_full_name())
    job_seeker_link.short_description = "Job Seeker"

    def job_link(self, obj):
        if obj.job:
            url = reverse('admin:jobs_job_change', args=[obj.job.id])
            return format_html('<a href="{}">{}</a>', url, obj.job.title)
        return "-"
    job_link.short_description = "Job"

    def unread_display(self, obj):
        return f"R:{obj.unread_by_recruiter} | S:{obj.unread_by_job_seeker}"
    unread_display.short_description = "Unread (R|S)"

    def archive_conversations(self, request, queryset):
        queryset.update(is_archived=True)
        self.message_user(request, f"{queryset.count()} conversation(s) archived.")
    archive_conversations.short_description = "Archive selected conversations"

    def unarchive_conversations(self, request, queryset):
        queryset.update(is_archived=False)
        self.message_user(request, f"{queryset.count()} conversation(s) unarchived.")
    unarchive_conversations.short_description = "Unarchive selected conversations"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'conversation_link',
        'sender_link',
        'receiver_link',
        'truncated_content',
        'message_type',
        'status',
        'created_at',
        'read_at'
    )
    list_filter = (
        'message_type',
        'status',
        'is_system_message',
        'created_at',
        'conversation__job__title'
    )
    search_fields = (
        'content',
        'sender__email',
        'sender__first_name',
        'sender__last_name',
        'receiver__email',
        'receiver__first_name',
        'receiver__last_name'
    )
    readonly_fields = (
        'conversation',
        'sender',
        'receiver',
        'created_at',
        'updated_at',
        'read_at'
    )
    fieldsets = (
        ('Message Details', {
            'fields': ('conversation', 'sender', 'receiver', 'content')
        }),
        ('Metadata', {
            'fields': ('message_type', 'status', 'is_system_message', 'attachments')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_inappropriate', 'delete_selected_messages']

    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">Conv #{}</a>', url, obj.conversation.id)
    conversation_link.short_description = "Conversation"

    def sender_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.get_full_name())
    sender_link.short_description = "Sender"

    def receiver_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.receiver.id])
        return format_html('<a href="{}">{}</a>', url, obj.receiver.get_full_name())
    receiver_link.short_description = "Receiver"

    def truncated_content(self, obj):
        return obj.content[:75] + "..." if len(obj.content) > 75 else obj.content
    truncated_content.short_description = "Content"

    def mark_as_inappropriate(self, request, queryset):
        # For example, set status to 'flagged' (assuming status field exists)
        # If your Message model has a 'status' field with choices, update accordingly.
        queryset.update(status='flagged')
        self.message_user(request, f"{queryset.count()} message(s) flagged as inappropriate.")
    mark_as_inappropriate.short_description = "Flag selected messages as inappropriate"

    def delete_selected_messages(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} message(s) deleted.")
    delete_selected_messages.short_description = "Delete selected messages (permanent)"


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_link', 'file_name', 'file_type', 'file_size_display', 'uploaded_at')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('file_name', 'message__content')
    readonly_fields = ('message', 'file_name', 'file_type', 'file_size', 'uploaded_at', 'file')

    def message_link(self, obj):
        url = reverse('admin:chat_message_change', args=[obj.message.id])
        return format_html('<a href="{}">Message #{}</a>', url, obj.message.id)
    message_link.short_description = "Message"

    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = "Size"


@admin.register(ConversationSettings)
class ConversationSettingsAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'message_notifications', 'email_notifications', 'updated_at')
    list_filter = ('message_notifications', 'email_notifications', 'sound_notifications')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('user',)

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    user_link.short_description = "User"


# TypingIndicator model is no longer registered