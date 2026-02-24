# notifications/tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_interview_reminders():
    """Send reminders for interviews happening in the next 24 hours"""
    try:
        from notifications.utils import check_and_create_interview_reminders
        count = check_and_create_interview_reminders()
        logger.info(f"Created {count} interview reminder notifications")
        return f"Created {count} interview reminders"
    except Exception as e:
        logger.error(f"Error sending interview reminders: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def generate_job_recommendations():
    """Generate job recommendations for active job seekers"""
    try:
        from notifications.utils import create_job_recommendation_notifications
        count = create_job_recommendation_notifications()
        logger.info(f"Created {count} job recommendation notifications")
        return f"Created {count} job recommendations"
    except Exception as e:
        logger.error(f"Error generating job recommendations: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def send_profile_completion_reminders():
    """Send reminders to job seekers with incomplete profiles"""
    try:
        from notifications.utils import send_profile_completion_reminders
        count = send_profile_completion_reminders()
        logger.info(f"Created {count} profile completion reminder notifications")
        return f"Created {count} profile completion reminders"
    except Exception as e:
        logger.error(f"Error sending profile reminders: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def cleanup_old_notifications():
    """Clean up old notifications to prevent database bloat"""
    try:
        from notifications.utils import cleanup_old_notifications
        count = cleanup_old_notifications()
        logger.info(f"Cleaned up {count} old notifications")
        return f"Cleaned up {count} old notifications"
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        return f"Error: {str(e)}"