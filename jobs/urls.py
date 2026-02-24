# jobs/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobViewSet, featured_jobs_homepage, DepartmentViewSet, get_similar_jobs

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'departments', DepartmentViewSet, basename='department')
urlpatterns = [
    path('', include(router.urls)),
    path('featured-jobs/homepage/', featured_jobs_homepage, name='featured-jobs-homepage'),
    path('jobs/<int:job_id>/similar/', get_similar_jobs, name='similar-jobs'),
]