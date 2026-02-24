from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import EmailTokenObtainPairView, UserRegistrationView, CheckEmailView, CurrentUserView, CurrentRecruiterView, JobSeekerProfileView, ExperienceListCreateView, ExperienceDetailView, EducationListCreateView, EducationDetailView, SkillListCreateView, SkillDetailView, RecruiterProfileView, CompanyProfileView, PublicRecruiterProfileView


urlpatterns = [
    path('token/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/register/', UserRegistrationView.as_view(), name='user_register'),
    # path('user/me/', CurrentUserView.as_view(), name='current_user'),
    path('user/check-email/', CheckEmailView.as_view(), name='check-email'),
    path('fetch/user/me/', CurrentUserView.as_view(), name='current-user'),
    path('recruiter/me/', CurrentRecruiterView.as_view(), name='current-recruiter'),
    # Job Seeker Profile URLs
    path('job-seeker/profile/', JobSeekerProfileView.as_view(), name='job-seeker-profile'),
    
    # Experience URLs
    path('job-seeker/experiences/', ExperienceListCreateView.as_view(), name='experience-list'),
    path('job-seeker/experiences/<int:pk>/', ExperienceDetailView.as_view(), name='experience-detail'),
    
    # Education URLs
    path('job-seeker/educations/', EducationListCreateView.as_view(), name='education-list'),
    path('job-seeker/educations/<int:pk>/', EducationDetailView.as_view(), name='education-detail'),
    
    # Skills URLs
    path('job-seeker/skills/', SkillListCreateView.as_view(), name='skill-list'),
    path('job-seeker/skills/<int:pk>/', SkillDetailView.as_view(), name='skill-detail'),

    path('recruiter/profile/', RecruiterProfileView.as_view(), name='recruiter-profile'),
    path('recruiter/company/', CompanyProfileView.as_view(), name='company-profile'),

    path('recruiters/<int:pk>/public/', PublicRecruiterProfileView.as_view(), name='public-recruiter'),
]