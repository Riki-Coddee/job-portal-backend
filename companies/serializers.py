from rest_framework import serializers
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    total_recruiters = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['created_at']

class CompanyBasicSerializer(serializers.ModelSerializer):
    """Basic company info for dropdowns/lists"""
    class Meta:
        model = Company
        fields = ['id', 'name', 'industry', 'location']
