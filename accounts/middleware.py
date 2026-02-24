# accounts/middleware.py
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class UpdateLastActivityMiddleware(MiddlewareMixin):
    """
    Middleware to update user's last activity time on every request
    """
    def process_response(self, request, response):
        # Only update for authenticated users
        if request.user.is_authenticated:
            # Use update to avoid race conditions and extra queries
            User.objects.filter(id=request.user.id).update(
                last_activity=timezone.now(),
                is_online=True
            )
        return response