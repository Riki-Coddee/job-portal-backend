# chat/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'conversations', views.ConversationViewSet, basename='conversation')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Messages nested under conversations
    path('conversations/<int:conversation_pk>/messages/', 
         views.MessageViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='conversation-messages'),
    
    # Typing indicator
    path('conversations/<int:conversation_id>/typing/', 
         views.TypingIndicatorView.as_view(), 
         name='typing-indicator'),
    
    # Online status endpoints
    path('users/<int:user_id>/online-status/', 
         views.get_user_online_status, 
         name='user-online-status'),
    path('users/online-status/batch/', 
         views.get_users_online_status, 
         name='users-online-status-batch'),
]