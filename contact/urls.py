# contact/urls.py
from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('faqs/', views.FAQListView.as_view(), name='faq-list'),
    path('contact/', views.ContactMessageCreateView.as_view(), name='contact-create'),
    
]