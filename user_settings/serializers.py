from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserSettings, TeamMember, TeamInvite

User = get_user_model()


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        exclude = ['user', 'created_at', 'updated_at']


class NotificationSettingsSerializer(serializers.Serializer):
    email = serializers.JSONField()
    push = serializers.JSONField()
    inApp = serializers.JSONField()


class SecuritySettingsSerializer(serializers.Serializer):
    twoFactor = serializers.BooleanField(source='two_factor_enabled')
    loginAlerts = serializers.BooleanField(source='login_alerts')
    sessionTimeout = serializers.IntegerField(source='session_timeout')
    ipWhitelist = serializers.BooleanField(source='ip_whitelist_enabled')


class AppearanceSettingsSerializer(serializers.Serializer):
    theme = serializers.CharField()
    density = serializers.CharField()
    fontSize = serializers.CharField(source='font_size')
    compactMode = serializers.BooleanField(source='compact_mode')


class GeneralSettingsSerializer(serializers.Serializer):
    language = serializers.CharField()
    timezone = serializers.CharField()
    dateFormat = serializers.CharField(source='date_format')
    autoSave = serializers.BooleanField(source='auto_save')
    emailDigest = serializers.CharField(source='email_digest')


class CombinedSettingsSerializer(serializers.Serializer):
    general = GeneralSettingsSerializer(source='*')
    notifications = serializers.SerializerMethodField()
    security = SecuritySettingsSerializer(source='*')
    appearance = AppearanceSettingsSerializer(source='*')
    
    def get_notifications(self, obj):
        return {
            'email': obj.email_notifications,
            'push': obj.push_notifications,
            'inApp': obj.in_app_notifications,
        }


class ChangePasswordSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(required=True)
    newPassword = serializers.CharField(required=True, min_length=8)
    confirmPassword = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['newPassword'] != data['confirmPassword']:
            raise serializers.ValidationError({"confirmPassword": "Passwords do not match"})
        return data


class TeamMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamMember
        fields = ['id', 'name', 'email', 'role', 'status']
    
    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class InviteTeamMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=TeamMember.ROLE_CHOICES)


class BillingInfoSerializer(serializers.Serializer):
    plan = serializers.CharField()
    nextBilling = serializers.DateField()
    paymentMethod = serializers.DictField()
    invoices = serializers.ListField()


class ExportDataSerializer(serializers.Serializer):
    data = serializers.JSONField()
    format = serializers.ChoiceField(choices=['json', 'csv'])