from rest_framework import serializers

class DashboardStatSerializer(serializers.Serializer):
    title = serializers.CharField()
    value = serializers.CharField()
    change = serializers.CharField()
    trend = serializers.CharField()
    
class ActivitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    candidate = serializers.CharField()
    action = serializers.CharField()
    job = serializers.CharField()
    time = serializers.CharField()
    status = serializers.CharField()
    icon = serializers.CharField()
    
class JobPerformanceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    applications = serializers.IntegerField()
    status = serializers.CharField()
    match = serializers.CharField()
    status_breakdown = serializers.DictField()