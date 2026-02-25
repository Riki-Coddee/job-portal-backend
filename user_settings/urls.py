from django.urls import path
from . import views

app_name = 'user_settings'

urlpatterns = [
    # Settings endpoints
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # Team management
    path('team/', views.TeamMemberListView.as_view(), name='team-list'),
    path('team/<int:member_id>/', views.TeamMemberDetailView.as_view(), name='team-detail'),
    
    # Billing and data
    path('billing/', views.BillingInfoView.as_view(), name='billing'),
    path('export-data/', views.ExportDataView.as_view(), name='export-data'),
    
    # Account actions
    path('delete-account/', views.DeleteAccountView.as_view(), name='delete-account'),
    path('signout-all/', views.SignOutAllView.as_view(), name='signout-all'),
]