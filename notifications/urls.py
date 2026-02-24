# notifications/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, notification_stats, test_notification

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('notifications/stats/', notification_stats, name='notification-stats'),
    path('notifications/test/', test_notification, name='test-notification'),
]