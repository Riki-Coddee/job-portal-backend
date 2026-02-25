import secrets
import json
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from .models import UserSettings, TeamMember, TeamInvite
from .serializers import (
    CombinedSettingsSerializer, ChangePasswordSerializer,
    TeamMemberSerializer, InviteTeamMemberSerializer,
    ExportDataSerializer, BillingInfoSerializer
)

User = get_user_model()


class SettingsView(APIView):
    """Get and update user settings"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        settings, created = UserSettings.objects.get_or_create(user=request.user)
        serializer = CombinedSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        settings, created = UserSettings.objects.get_or_create(user=request.user)
        
        # Update general settings
        if 'general' in request.data:
            general = request.data['general']
            settings.language = general.get('language', settings.language)
            settings.timezone = general.get('timezone', settings.timezone)
            settings.date_format = general.get('dateFormat', settings.date_format)
            settings.auto_save = general.get('autoSave', settings.auto_save)
            settings.email_digest = general.get('emailDigest', settings.email_digest)
        
        # Update notification settings
        if 'notifications' in request.data:
            notifications = request.data['notifications']
            if 'email' in notifications:
                settings.email_notifications = notifications['email']
            if 'push' in notifications:
                settings.push_notifications = notifications['push']
            if 'inApp' in notifications:
                settings.in_app_notifications = notifications['inApp']
        
        # Update security settings
        if 'security' in request.data:
            security = request.data['security']
            settings.two_factor_enabled = security.get('twoFactor', settings.two_factor_enabled)
            settings.login_alerts = security.get('loginAlerts', settings.login_alerts)
            settings.session_timeout = security.get('sessionTimeout', settings.session_timeout)
            settings.ip_whitelist_enabled = security.get('ipWhitelist', settings.ip_whitelist_enabled)
        
        # Update appearance settings
        if 'appearance' in request.data:
            appearance = request.data['appearance']
            settings.theme = appearance.get('theme', settings.theme)
            settings.density = appearance.get('density', settings.density)
            settings.font_size = appearance.get('fontSize', settings.font_size)
            settings.compact_mode = appearance.get('compactMode', settings.compact_mode)
        
        settings.save()
        
        serializer = CombinedSettingsSerializer(settings)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['currentPassword']):
                return Response(
                    {'currentPassword': ['Current password is incorrect']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializer.validated_data['newPassword'])
            user.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeamMemberListView(APIView):
    """List and manage team members"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Get user's company from recruiter profile
        if hasattr(request.user, 'recruiter') and request.user.recruiter.company:
            company = request.user.recruiter.company
            members = TeamMember.objects.filter(company=company).select_related('user')
            serializer = TeamMemberSerializer(members, many=True)
            return Response(serializer.data)
        return Response([])
    
    def post(self, request):
        if not hasattr(request.user, 'recruiter') or not request.user.recruiter.company:
            return Response(
                {'error': 'You must be a recruiter with a company to invite members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InviteTeamMemberSerializer(data=request.data)
        if serializer.is_valid():
            company = request.user.recruiter.company
            email = serializer.validated_data['email']
            role = serializer.validated_data['role']
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
                # Create team member if user exists
                member, created = TeamMember.objects.get_or_create(
                    company=company,
                    user=user,
                    defaults={
                        'role': role,
                        'status': 'active',
                        'invited_by': request.user,
                        'invited_email': email,
                    }
                )
                if not created:
                    return Response(
                        {'error': 'User is already a team member'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Send notification email
                self.send_invite_email(user, company, request.user)
                
            except User.DoesNotExist:
                # Create invite token for new user
                token = secrets.token_urlsafe(32)
                expires_at = timezone.now() + timedelta(days=7)
                
                invite = TeamInvite.objects.create(
                    company=company,
                    email=email,
                    role=role,
                    invited_by=request.user,
                    token=token,
                    expires_at=expires_at
                )
                
                # Send invitation email with signup link
                self.send_invitation_email(email, company, token, request.user)
            
            return Response({'message': f'Invitation sent to {email}'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def send_invite_email(self, user, company, inviter):
        """Send email to existing user"""
        subject = f"You've been added to {company.name} on HirePro"
        message = f"""
        Hi {user.first_name or user.email},
        
        {inviter.get_full_name() or inviter.email} has added you to {company.name} on HirePro.
        You now have access to team features.
        
        Login to your account to get started: {settings.FRONTEND_URL}/login
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    
    def send_invitation_email(self, email, company, token, inviter):
        """Send invitation email to new user"""
        signup_url = f"{settings.FRONTEND_URL}/register?invite={token}&email={email}"
        subject = f"Join {company.name} on HirePro"
        message = f"""
        You've been invited to join {company.name} on HirePro!
        
        {inviter.get_full_name() or inviter.email} has invited you to join their team.
        
        Click the link below to create your account and get started:
        {signup_url}
        
        This invitation expires in 7 days.
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


class TeamMemberDetailView(APIView):
    """Update or remove team members"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, member_id):
        try:
            member = TeamMember.objects.get(id=member_id, company__recruiters__user=request.user)
            member.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TeamMember.DoesNotExist:
            return Response(
                {'error': 'Team member not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def patch(self, request, member_id):
        try:
            member = TeamMember.objects.get(id=member_id, company__recruiters__user=request.user)
            role = request.data.get('role')
            if role and role in dict(TeamMember.ROLE_CHOICES):
                member.role = role
                member.save()
                serializer = TeamMemberSerializer(member)
                return Response(serializer.data)
            return Response(
                {'error': 'Invalid role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except TeamMember.DoesNotExist:
            return Response(
                {'error': 'Team member not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class BillingInfoView(APIView):
    """Get billing information"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # This would typically come from a subscription service
        # Example data structure
        billing_data = {
            'plan': 'professional',
            'nextBilling': timezone.now().date() + timedelta(days=30),
            'paymentMethod': {
                'type': 'visa',
                'last4': '4242',
                'expDate': '12/25',
            },
            'invoices': [
                {
                    'id': 'INV-001',
                    'date': (timezone.now() - timedelta(days=30)).date(),
                    'amount': '$49.00',
                    'status': 'paid',
                },
                {
                    'id': 'INV-002',
                    'date': timezone.now().date(),
                    'amount': '$49.00',
                    'status': 'paid',
                },
            ],
        }
        return Response(billing_data)


class ExportDataView(APIView):
    """Export user data"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ExportDataSerializer(data=request.data)
        if serializer.is_valid():
            # Gather all user data
            user_data = {
                'user': {
                    'email': request.user.email,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'role': request.user.role,
                    'date_joined': request.user.date_joined.isoformat(),
                },
                'settings': UserSettingsSerializer(request.user.settings).data if hasattr(request.user, 'settings') else None,
                # Add more data as needed
            }
            
            if serializer.validated_data['format'] == 'json':
                return Response(user_data)
            else:
                # Handle CSV export
                import csv
                from django.http import HttpResponse
                
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="user_data.csv"'
                
                writer = csv.writer(response)
                writer.writerow(['Field', 'Value'])
                for key, value in self.flatten_dict(user_data).items():
                    writer.writerow([key, value])
                
                return response
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def flatten_dict(self, d, parent_key='', sep='_'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)


class DeleteAccountView(APIView):
    """Delete user account"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        user = request.user
        # Optional: Send confirmation email
        send_mail(
            'Account Deleted',
            f'Your account ({user.email}) has been successfully deleted.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SignOutAllView(APIView):
    """Sign out from all devices"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # This will invalidate all sessions except current one
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        # Get all sessions for this user
        user_sessions = []
        for session in Session.objects.filter(expire_date__gte=timezone.now()):
            data = session.get_decoded()
            if data.get('_auth_user_id') == str(request.user.id):
                user_sessions.append(session.session_key)
        
        # Delete all sessions except current
        current_session = request.session.session_key
        for session_key in user_sessions:
            if session_key != current_session:
                Session.objects.filter(session_key=session_key).delete()
        
        return Response({'message': 'Signed out from all other devices'})