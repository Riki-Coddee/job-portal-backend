from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.RecruiterDashboardAPIView.as_view(), name='recruiter-dashboard'),
    path('analytics/', views.AnalyticsAPIView.as_view(), name='analytics'),
    path('quick-stats/', views.QuickStatsAPIView.as_view(), name='quick-stats'),
]