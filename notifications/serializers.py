# notifications/serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'action_url', 'is_read', 'priority', 'created_at',
            'time_ago', 'icon', 'application', 'interview', 'job'
        ]
        read_only_fields = fields
    
    def get_time_ago(self, obj):
        return obj.time_ago
    
    def get_icon(self, obj):
        return obj.icon

class MarkAsReadSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    mark_all = serializers.BooleanField(default=False)