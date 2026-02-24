# applications/urls.py - Update with new endpoints

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ApplicationViewSet, InterviewViewSet,
    CandidateTagViewSet, CandidateCommunicationViewSet, 
    JobSeekerApplicationViewSet, apply_to_job,
    sync_chat_conversations, get_application_conversations,
    application_stats, update_status, toggle_favorite,
    update_score, schedule_interview, add_note, delete_app,
    job_stats, jobseeker_application_stats, get_jobseeker_interviews
)

router = DefaultRouter()
router.register(r'applications/my-applications', JobSeekerApplicationViewSet, basename='jobseeker-application')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'interviews', InterviewViewSet, basename='interview')
router.register(r'tags', CandidateTagViewSet, basename='tag')
router.register(r'communications', CandidateCommunicationViewSet, basename='communication')

urlpatterns = [
    path('', include(router.urls)),
    path('applications/apply-to-job/<int:job_id>/', apply_to_job, name='apply-to-job'),
    path('applications/sync-chat-conversations/', sync_chat_conversations, name='sync-chat-conversations'),
    path('applications/conversations/', get_application_conversations, name='application-conversations'),
    
    # Job seeker specific endpoints
    path('applications/my-stats/', jobseeker_application_stats, name='jobseeker-stats'),
    
    # Recruiter dashboard endpoints
    path('applications/stats/', application_stats, name='application-stats'),
    path('applications/<int:pk>/update_status/', update_status, name='update-status'),
    path('applications/<int:pk>/toggle_favorite/', toggle_favorite, name='toggle-favorite'),
    path('applications/<int:pk>/update_score/', update_score, name='update-score'),
    path('applications/<int:pk>/schedule_interview/', schedule_interview, name='schedule-interview'),
    path('applications/<int:pk>/add_note/', add_note, name='add-note'),
    path('applications/<int:pk>/', delete_app, name='delete-app'),
    path('jobs/stats/', job_stats, name='job-stats'),
     path('applications/my-interviews/', get_jobseeker_interviews, name='jobseeker-interviews'),
]