# contact/serializers.py
from rest_framework import serializers
from .models import FAQ, ContactMessage

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer']


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'category', 'subject', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']


class ContactMessageDetailSerializer(serializers.ModelSerializer):
    """For admin use - includes all fields"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = ContactMessage
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'ip_address', 'user_agent']