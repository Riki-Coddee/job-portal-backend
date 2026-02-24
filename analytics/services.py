from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from accounts.models import Recruiter, CustomUser
from applications.models import Application, Interview
from jobs.models import Job
from chat.models import Conversation, Message
import calendar

class RecruiterDashboardService:
    """Service to fetch and calculate dashboard data"""
    
    def __init__(self, recruiter):
        self.recruiter = recruiter
        self.user = recruiter.user
        
    def get_dashboard_stats(self):
        """Get all stats for recruiter dashboard"""
        # Get all jobs posted by this recruiter
        recruiter_jobs = Job.objects.filter(recruiter=self.recruiter)
        
        # Get all applications for recruiter's jobs
        applications = Application.objects.filter(job__recruiter=self.recruiter)
        
        # Calculate stats
        stats = {
            'total_applications': self._get_total_applications(applications),
            'active_jobs': self._get_active_jobs(recruiter_jobs),
            'interview_scheduled': self._get_interviews_scheduled(),
            'avg_time_to_hire': self._get_avg_time_to_hire(applications),
            'unread_messages': self._get_unread_messages(),
            'applications_today': self._get_applications_today(applications),
            'interviews_today': self._get_interviews_today(),
            'hired_candidates': self._get_hired_candidates(applications),  # Add this
        }
        
        return stats
    
    def _get_total_applications(self, applications):
        """Get total applications with change from last month"""
        total = applications.count()
        
        # Calculate change from last month
        last_month = timezone.now() - timedelta(days=30)
        last_month_count = applications.filter(
            applied_at__lt=last_month
        ).count()
        
        change = self._calculate_percentage_change(last_month_count, total)
        
        return {
            'value': total,
            'change': f"{change}%",
            'trend': 'up' if change > 0 else 'down'
        }
    
    def _get_active_jobs(self, jobs):
        """Get active jobs count"""
        active = jobs.filter(is_active=True, is_published=True).count()
        total = jobs.count()
        
        return {
            'value': active,
            'change': f"{total - active} inactive",
            'trend': 'up' if active > 0 else 'down'
        }
    
    def _get_interviews_scheduled(self):
        """Get scheduled interviews count"""
        interviews = Interview.objects.filter(
            application__job__recruiter=self.recruiter,
            status='scheduled'
        ).count()
        
        # Get interviews from last month for comparison
        last_month = timezone.now() - timedelta(days=30)
        last_month_interviews = Interview.objects.filter(
            application__job__recruiter=self.recruiter,
            status='scheduled',
            scheduled_date__gte=last_month
        ).count()
        
        change = self._calculate_percentage_change(last_month_interviews, interviews)
        
        return {
            'value': interviews,
            'change': f"{change}%",
            'trend': 'up' if change > 0 else 'down'
        }
    
    def _get_avg_time_to_hire(self, applications):
        """Calculate average time from application to offer/hire"""
        # Include both accepted and hired applications
        hired_applications = applications.filter(
            status__in=['accepted', 'hired'],
            offer_date__isnull=False
        )
        
        if hired_applications.exists():
            total_days = 0
            for app in hired_applications:
                if app.offer_date and app.applied_at:
                    days = (app.offer_date - app.applied_at).days
                    total_days += days
            
            avg_days = total_days / hired_applications.count()
            
            # Compare with previous period
            last_month = timezone.now() - timedelta(days=30)
            previous_hires = applications.filter(
                status__in=['accepted', 'hired'],
                offer_date__isnull=False,
                offer_date__lt=last_month
            )
            
            if previous_hires.exists():
                prev_total_days = 0
                for app in previous_hires:
                    if app.offer_date and app.applied_at:
                        days = (app.offer_date - app.applied_at).days
                        prev_total_days += days
                
                prev_avg_days = prev_total_days / previous_hires.count()
                change_days = prev_avg_days - avg_days
                
                return {
                    'value': f"{avg_days:.1f} days",
                    'change': f"-{abs(change_days):.1f} days" if change_days > 0 else f"+{abs(change_days):.1f} days",
                    'trend': 'up' if change_days > 0 else 'down'
                }
        
        return {
            'value': 'N/A',
            'change': '0%',
            'trend': 'neutral'
        }
    
    def _get_unread_messages(self):
        """Get unread messages count"""
        conversations = Conversation.objects.filter(recruiter=self.recruiter)
        unread = sum(conv.unread_by_recruiter for conv in conversations)
        
        return {
            'value': unread,
            'change': f"{unread} unread",
            'trend': 'up' if unread > 0 else 'down'
        }
    
    def _get_applications_today(self, applications):
        """Get applications received today"""
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        return applications.filter(
            applied_at__range=[today_start, today_end]
        ).count()
    
    def _get_interviews_today(self):
        """Get interviews scheduled for today"""
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        return Interview.objects.filter(
            application__job__recruiter=self.recruiter,
            scheduled_date__range=[today_start, today_end],
            status='scheduled'
        ).count()
    
    def get_recent_activities(self, limit=10):
        """Get recent activities for dashboard"""
        activities = []
        
        # Recent applications
        recent_apps = Application.objects.filter(
            job__recruiter=self.recruiter
        ).select_related('seeker__user', 'job').order_by('-applied_at')[:5]
        
        for app in recent_apps:
            activities.append({
                'id': app.id,
                'type': 'application',
                'candidate': f"{app.seeker.user.first_name} {app.seeker.user.last_name}",
                'action': 'applied for',
                'job': app.job.title,
                'time': self._get_time_ago(app.applied_at),
                'status': app.status,
                'icon': 'application'
            })
        
        # Recent interviews
        recent_interviews = Interview.objects.filter(
            application__job__recruiter=self.recruiter
        ).select_related('application__seeker__user', 'application__job').order_by('-created_at')[:5]
        
        for interview in recent_interviews:
            activities.append({
                'id': interview.id,
                'type': 'interview',
                'candidate': f"{interview.application.seeker.user.first_name} {interview.application.seeker.user.last_name}",
                'action': f"{interview.status} interview for",  # FIXED: Changed single quote to double quote
                'job': interview.application.job.title,
                'time': self._get_time_ago(interview.created_at),
                'status': interview.status,
                'icon': 'interview'
            })
        
        # Sort by time and return limited results
        activities.sort(key=lambda x: x['time'], reverse=True)
        return activities[:limit]
    
    def get_top_performing_jobs(self, limit=5):
        """Get top performing jobs by application count"""
        jobs = Job.objects.filter(recruiter=self.recruiter).annotate(
            application_count=Count('applications'),
            avg_match_score=Avg('applications__match_score')
        ).order_by('-application_count')[:limit]
        
        result = []
        for job in jobs:
            # Calculate match score average
            avg_score = job.avg_match_score or 0
            applications = job.applications.all()
            
            # Get status breakdown
            status_counts = applications.values('status').annotate(count=Count('status'))
            
            result.append({
                'id': job.id,
                'title': job.title,
                'applications': job.application_count,
                'status': 'active' if job.is_active else 'inactive',
                'match': f"{avg_score:.0f}%",
                'status_breakdown': {item['status']: item['count'] for item in status_counts}
            })
        
        return result
    
    def _calculate_percentage_change(self, old_value, new_value):
        """Calculate percentage change between two values"""
        if old_value == 0:
            return 100 if new_value > 0 else 0
        return round(((new_value - old_value) / old_value) * 100, 1)
    
    def _get_time_ago(self, timestamp):
        """Convert timestamp to human readable time ago"""
        now = timezone.now()
        diff = now - timestamp
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

    def _get_hired_candidates(self, applications):
        """Get hired candidates count"""
        # Count both accepted and hired statuses
        hired = applications.filter(status__in=['accepted', 'hired']).count()
        
        # Calculate change from last month
        last_month = timezone.now() - timedelta(days=30)
        last_month_hired = applications.filter(
            status__in=['accepted', 'hired'],
            hired_date__isnull=False,
            hired_date__lt=last_month
        ).count()
        
        change = self._calculate_percentage_change(last_month_hired, hired)
        
        return {
            'value': hired,
            'change': f"{change}%",
            'trend': 'up' if change > 0 else 'down'
        }

class AnalyticsService:
    """Service for detailed analytics"""
    
    def __init__(self, recruiter):
        self.recruiter = recruiter
        
    def get_analytics_overview(self, time_range='month'):
        """Get detailed analytics overview"""
        date_range = self._get_date_range(time_range)
        
        applications = Application.objects.filter(
            job__recruiter=self.recruiter,
            applied_at__range=date_range
        )
        
        interviews = Interview.objects.filter(
            application__job__recruiter=self.recruiter,
            scheduled_date__range=date_range
        )
        
        return {
            'applications_over_time': self._get_applications_over_time(applications, time_range),
            'hire_rate': self._calculate_hire_rate(applications),
            'total_hires': applications.filter(status__in=['accepted', 'hired']).count(),  # Add this
            'source_breakdown': self._get_source_breakdown(applications),
            'department_performance': self._get_department_performance(time_range),
            'candidate_quality': self._get_candidate_quality(applications),
            'time_metrics': self._get_time_metrics(applications, interviews),
        }

    def _get_date_range(self, time_range):
        """Get date range based on time filter"""
        now = timezone.now()
        
        if time_range == 'week':
            start_date = now - timedelta(days=7)
        elif time_range == 'month':
            start_date = now - timedelta(days=30)
        elif time_range == 'quarter':
            start_date = now - timedelta(days=90)
        elif time_range == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)
        
        return [start_date, now]
    
    def _get_applications_over_time(self, applications, time_range):
        """Get applications count grouped by time period"""
        if time_range == 'week':
            # Group by day
            dates = {}
            for i in range(7):
                date = (timezone.now() - timedelta(days=i)).date()
                dates[date.strftime('%a')] = applications.filter(
                    applied_at__date=date
                ).count()
            return dates
            
        elif time_range == 'month':
            # Group by week
            weeks = {}
            for i in range(4):
                week_start = timezone.now() - timedelta(days=7*(i+1))
                week_end = timezone.now() - timedelta(days=7*i)
                week_key = f"Week {i+1}"
                weeks[week_key] = applications.filter(
                    applied_at__range=[week_start, week_end]
                ).count()
            return weeks
            
        elif time_range == 'year':
            # Group by month
            months = {}
            for i in range(12):
                month_date = timezone.now() - timedelta(days=30*(i+1))
                month_name = calendar.month_name[month_date.month]
                month_key = f"{month_name[:3]}"
                months[month_key] = applications.filter(
                    applied_at__month=month_date.month,
                    applied_at__year=month_date.year
                ).count()
            return months
        
        # Default: return by day for the last 7 days
        dates = {}
        for i in range(7):
            date = (timezone.now() - timedelta(days=i)).date()
            dates[date.strftime('%a')] = applications.filter(
                applied_at__date=date
            ).count()
        return dates
    
    def _calculate_hire_rate(self, applications):
        """Calculate hire rate percentage"""
        total = applications.count()
        if total == 0:
            return 0
        
        # Include both 'accepted' and 'hired' statuses as hires
        hires = applications.filter(status__in=['accepted', 'hired']).count()
        return round((hires / total) * 100, 1)
    
    def _get_source_breakdown(self, applications):
        """Breakdown applications by source (you need to track this in your model)"""
        # Since you don't have source tracking yet, return empty data
        # You can implement this later when you add source field to Application model
        return {}
    
    def _get_department_performance(self, time_range):
        """Get performance metrics by department"""
        date_range = self._get_date_range(time_range)
        
        departments = {}
        jobs = Job.objects.filter(
            recruiter=self.recruiter,
            created_at__range=date_range
        ).select_related('department')
        
        for job in jobs:
            if job.department:
                dept_name = job.department.name
                if dept_name not in departments:
                    departments[dept_name] = {
                        'applications': 0,
                        'interviews': 0,
                        'hires': 0,
                        'open_roles': 0
                    }
                
                # Get applications for this job
                job_applications = job.applications.all()
                departments[dept_name]['applications'] += job_applications.count()
                
                # Count interviews
                departments[dept_name]['interviews'] += job_applications.filter(
                    interviews__status='scheduled'
                ).count()
                
                # Count hires (both accepted and hired statuses)
                departments[dept_name]['hires'] += job_applications.filter(
                    status__in=['accepted', 'hired']
                ).count()
        
        # Add open roles count
        active_jobs = Job.objects.filter(
            recruiter=self.recruiter,
            is_active=True,
            is_published=True
        )
        
        for job in active_jobs:
            if job.department:
                dept_name = job.department.name
                if dept_name in departments:
                    departments[dept_name]['open_roles'] += 1
        
        return departments
    
    def _get_candidate_quality(self, applications):
        """Analyze candidate quality metrics"""
        if not applications.exists():
            return {
                'avg_match_score': 0,
                'top_skills': [],
                'experience_levels': {}
            }
        
        # Average match score
        avg_score = applications.aggregate(avg=Avg('match_score'))['avg'] or 0
        
        # Top skills from applications
        all_skills = []
        for app in applications:
            if app.skills and isinstance(app.skills, list):
                # Extract skill names from the skills JSONField
                for skill_data in app.skills:
                    if isinstance(skill_data, dict) and 'name' in skill_data:
                        all_skills.append(skill_data['name'])
        
        # Count skill occurrences
        from collections import Counter
        skill_counts = Counter(all_skills)
        top_skills = [skill[0] for skill in skill_counts.most_common(5)]
        
        # Since you don't have experience levels in your model yet
        # Return default empty data
        experience_levels = {}
        
        return {
            'avg_match_score': round(avg_score, 1),
            'top_skills': top_skills,
            'experience_levels': experience_levels
        }
    
    def _get_time_metrics(self, applications, interviews):
        """Get time-based metrics"""
        metrics = {}
        
        # Average time to first response
        responded_apps = applications.filter(last_message_at__isnull=False)
        if responded_apps.exists():
            total_hours = 0
            for app in responded_apps:
                if app.last_message_at and app.applied_at:
                    hours = (app.last_message_at - app.applied_at).total_seconds() / 3600
                    total_hours += hours
            metrics['avg_response_time'] = f"{total_hours / responded_apps.count():.1f} hours"
        else:
            metrics['avg_response_time'] = "N/A"
        
        # Interview completion rate
        total_interviews = interviews.count()
        completed_interviews = interviews.filter(status='completed').count()
        if total_interviews > 0:
            metrics['interview_completion_rate'] = f"{(completed_interviews / total_interviews) * 100:.1f}%"
        else:
            metrics['interview_completion_rate'] = "N/A"
        
        return metrics