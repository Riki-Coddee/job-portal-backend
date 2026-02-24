# jobs/views.py
from rest_framework import viewsets
from .models import Company
from .serializers import CompanySerializer
from rest_framework.permissions import AllowAny

class CompanyViewSet(viewsets.ModelViewSet):
    """
    Complete CRUD operations for Company model
    No authentication required
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    
    # Explicitly set empty authentication classes
    permission_classes = [AllowAny]