from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class UpdateLastActivityMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.user.is_authenticated and not request.path.startswith('/admin/'):
            User.objects.filter(id=request.user.id).update(
                last_activity=timezone.now(),
                is_online=True
            )
        return response