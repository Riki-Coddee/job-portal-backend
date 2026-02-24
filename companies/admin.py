from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from .models import Company
import json


class CompanyAdminForm(forms.ModelForm):
    """Custom form for Company admin with better field handling"""
    
    # Textareas for perks and awards with helpful placeholders
    perks_input = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Enter one perk per line\ne.g.:\nFlexible working hours\nHealth insurance\nRemote work options'
        }),
        required=False,
        label='Perks',
        help_text='Enter each perk on a new line'
    )
    
    awards_input = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Enter one award per line with year if available\ne.g.:\nBest IT Company 2023\nISO 9001:2015 Certification'
        }),
        required=False,
        label='Awards',
        help_text='Enter each award on a new line'
    )
    
    class Meta:
        model = Company
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate the text fields from JSON data
        if self.instance.pk:
            if self.instance.perks:
                self.fields['perks_input'].initial = '\n'.join(self.instance.perks)
            if self.instance.awards:
                self.fields['awards_input'].initial = '\n'.join(self.instance.awards)
    
    def save(self, commit=True):
        """Save the form data to the instance"""
        instance = super().save(commit=False)
        
        # Convert perks_input to JSON and save to perks field
        perks_text = self.cleaned_data.get('perks_input', '')
        if perks_text:
            instance.perks = [line.strip() for line in perks_text.split('\n') if line.strip()]
        else:
            instance.perks = []
        
        # Convert awards_input to JSON and save to awards field
        awards_text = self.cleaned_data.get('awards_input', '')
        if awards_text:
            instance.awards = [line.strip() for line in awards_text.split('\n') if line.strip()]
        else:
            instance.awards = []
        
        if commit:
            instance.save()
        
        return instance


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Enhanced admin for Companies with better perks/awards handling"""
    
    form = CompanyAdminForm
    
    list_display = (
        'name',
        'industry',
        'location',
        'website_link',
        'founded_year',
        'recruiters_count',
    )
    
    list_filter = (
        'industry',
        'founded_year',
        'company_size',
    )
    
    search_fields = (
        'name',
        'industry',
        'location',
        'description',
        'tagline',
        'email'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'logo',
                'tagline',
                'description',
                'industry'
            )
        }),
        ('Contact & Location', {
            'fields': (
                'location',
                'headquarters',
                'website',
                'email',
                'phone'
            )
        }),
        ('Company Details', {
            'fields': (
                'founded_year',
                'company_size',
                'culture_description'
            ),
            'classes': ('collapse',)
        }),
        ('Social Media', {
            'fields': (
                'linkedin_url',
                'twitter_url',
                'facebook_url',
                'instagram_url'
            ),
            'classes': ('collapse',)
        }),
        ('Perks & Benefits', {
            'fields': ('perks_input',),
            'description': 'Add all the perks and benefits your company offers',
        }),
        ('Awards & Recognition', {
            'fields': ('awards_input',),
            'description': 'Add awards, certifications, and recognitions',
        }),
    )
    
    list_per_page = 25
    ordering = ('name',)
    
    def website_link(self, obj):
        """Display website as clickable link"""
        if obj.website:
            return format_html(
                '<a href="{}" target="_blank">🌐 Visit</a>',
                obj.website
            )
        return "-"
    website_link.short_description = 'Website'
    
    def recruiters_count(self, obj):
        """Display number of recruiters with link"""
        return obj.recruiters.count()
    recruiters_count.short_description = 'Recruiters'