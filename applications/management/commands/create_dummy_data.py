# create_dummy_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import CustomUser, JobSeeker, Recruiter
from jobs.models import Job
from applications.models import (
    Application, ApplicationNote, Interview, 
    CandidateTag, CandidateCommunication
)
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Create dummy data for applications'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating dummy application data...')
        
        # Clear existing data
        Application.objects.all().delete()
        ApplicationNote.objects.all().delete()
        Interview.objects.all().delete()
        CandidateTag.objects.all().delete()
        CandidateCommunication.objects.all().delete()
        
        # Get existing recruiters and jobs
        recruiters = Recruiter.objects.all()
        if not recruiters.exists():
            self.stdout.write('No recruiters found. Creating a recruiter...')
            user = CustomUser.objects.create_user(
                email='recruiter@test.com',
                password='test123',
                first_name='John',
                last_name='Recruiter',
                role='recruiter'
            )
            recruiter = Recruiter.objects.create(
                user=user,
                phone='1234567890',
                company_name='TechCorp Inc.',
                company_description='A leading tech company'
            )
            recruiters = [recruiter]
        
        jobs = Job.objects.all()
        if not jobs.exists():
            self.stdout.write('No jobs found. Creating jobs...')
            for i in range(5):
                Job.objects.create(
                    recruiter=recruiters[0],
                    title=f'Job Title {i+1}',
                    company='TechCorp Inc.',
                    description=f'Description for job {i+1}',
                    location='Remote',
                    department='Engineering',
                    job_type='full_time',
                    remote_policy='remote',
                    salary_min=50000 + i * 10000,
                    salary_max=80000 + i * 10000,
                    currency='USD',
                    display_salary=True,
                    experience_level='mid',
                    requirements='Requirements here',
                    benefits='Benefits here',
                    is_active=True,
                    is_published=True,
                    publish_option='immediate',
                    published_at=timezone.now() - timedelta(days=30-i*5)
                )
            jobs = Job.objects.all()
        
        # Dummy candidate data matching frontend
        dummy_candidates = [
            {
                'name': 'Sarah Johnson',
                'email': 'sarah.j@email.com',
                'phone': '(415) 555-1234',
                'location': 'San Francisco, CA',
                'position': 'Senior Frontend Developer',
                'status': 'shortlisted',
                'score': 92,
                'experience': '8 years',
                'skills': ['React', 'TypeScript', 'Next.js', 'GraphQL'],
                'avatar_color': 'from-pink-500 to-rose-500'
            },
            {
                'name': 'Michael Chen',
                'email': 'michael.c@email.com',
                'phone': '(212) 555-9876',
                'location': 'New York, NY',
                'position': 'Full Stack Engineer',
                'status': 'interview',
                'score': 88,
                'experience': '6 years',
                'skills': ['Node.js', 'Python', 'AWS', 'MongoDB'],
                'avatar_color': 'from-blue-500 to-cyan-500'
            },
            {
                'name': 'Emma Wilson',
                'email': 'emma.w@email.com',
                'phone': '(617) 555-4567',
                'location': 'Boston, MA',
                'position': 'Product Manager',
                'status': 'new',
                'score': 78,
                'experience': '7 years',
                'skills': ['Product Strategy', 'Agile', 'Figma', 'SQL'],
                'avatar_color': 'from-purple-500 to-violet-500'
            },
            {
                'name': 'David Park',
                'email': 'david.p@email.com',
                'phone': '(310) 555-7890',
                'location': 'Los Angeles, CA',
                'position': 'DevOps Engineer',
                'status': 'rejected',
                'score': 65,
                'experience': '5 years',
                'skills': ['Docker', 'Kubernetes', 'Terraform', 'Linux'],
                'avatar_color': 'from-green-500 to-emerald-500'
            },
            {
                'name': 'Lisa Rodriguez',
                'email': 'lisa.r@email.com',
                'phone': '(305) 555-2345',
                'location': 'Miami, FL',
                'position': 'UX Designer',
                'status': 'offer',
                'score': 95,
                'experience': '9 years',
                'skills': ['Figma', 'Sketch', 'Adobe XD', 'User Research'],
                'avatar_color': 'from-orange-500 to-amber-500'
            },
            {
                'name': 'Alex Turner',
                'email': 'alex.t@email.com',
                'phone': '(503) 555-3456',
                'location': 'Portland, OR',
                'position': 'Data Scientist',
                'status': 'shortlisted',
                'score': 84,
                'experience': '4 years',
                'skills': ['Python', 'R', 'TensorFlow', 'SQL'],
                'avatar_color': 'from-indigo-500 to-blue-500'
            },
            {
                'name': 'James Wilson',
                'email': 'james.w@email.com',
                'phone': '(206) 555-6789',
                'location': 'Seattle, WA',
                'position': 'Backend Developer',
                'status': 'pending',
                'score': 72,
                'experience': '3 years',
                'skills': ['Java', 'Spring Boot', 'PostgreSQL', 'Redis'],
                'avatar_color': 'from-red-500 to-orange-500'
            },
            {
                'name': 'Sophia Lee',
                'email': 'sophia.l@email.com',
                'phone': '(312) 555-9012',
                'location': 'Chicago, IL',
                'position': 'Mobile Developer',
                'status': 'reviewed',
                'score': 81,
                'experience': '4 years',
                'skills': ['React Native', 'iOS', 'Android', 'Firebase'],
                'avatar_color': 'from-teal-500 to-green-500'
            },
        ]
        
        # Create job seekers and applications
        for i, candidate in enumerate(dummy_candidates):
            # Create or get job seeker user
            try:
                user = CustomUser.objects.get(email=candidate['email'])
            except CustomUser.DoesNotExist:
                first_name, last_name = candidate['name'].split(' ', 1)
                user = CustomUser.objects.create_user(
                    email=candidate['email'],
                    password='test123',
                    first_name=first_name,
                    last_name=last_name,
                    role='job_seeker'
                )
            
            # Create or get job seeker profile
            seeker, created = JobSeeker.objects.get_or_create(
                user=user,
                defaults={
                    'phone': candidate['phone'],
                    'location': candidate['location'],
                    'headline': candidate['position'],
                    'bio': f'Experienced {candidate["position"]} with {candidate["experience"]} in the industry.',
                    'experience_years': int(candidate['experience'].split()[0]),
                    'education_level': "Bachelor's Degree",
                    'expected_salary': 80000 + i * 10000,
                    'resume': None,
                    'profile_picture': None,
                    'is_available': True,
                }
            )
            
            # Find a matching job
            job = jobs[i % len(jobs)]
            
            # Create application
            applied_date = timezone.now() - timedelta(days=random.randint(1, 30))
            
            application = Application.objects.create(
                job=job,
                seeker=seeker,
                status=candidate['status'],
                match_score=candidate['score'],
                skills=candidate['skills'],
                experience_summary=candidate['experience'],
                applied_at=applied_date,
                last_active=timezone.now() - timedelta(hours=random.randint(1, 72)),
                last_viewed=timezone.now() - timedelta(days=random.randint(0, 7)) if random.choice([True, False]) else None,
                cover_letter=f"""Dear Hiring Manager,

I am writing to express my interest in the {candidate['position']} position at {job.company}. With {candidate['experience']} of experience in the field, I am confident in my ability to contribute effectively to your team.

My key skills include: {', '.join(candidate['skills'][:3])}.

I look forward to the opportunity to discuss how my skills and experience align with your needs.

Sincerely,
{candidate['name']}""",
                is_favorite=random.choice([True, False]),
                is_archived=False,
                recruiter_rating=random.randint(3, 5) if candidate['status'] in ['shortlisted', 'interview', 'offer'] else None,
                recruiter_notes=random.choice([
                    'Strong technical skills',
                    'Good cultural fit',
                    'Needs more experience',
                    'Excellent communication',
                    'Impressive portfolio',
                    ''
                ]),
                messages_count=random.randint(0, 5),
                last_message_at=timezone.now() - timedelta(days=random.randint(0, 5)) if random.choice([True, False]) else None,
            )
            
            # Add interview if status is interview
            if candidate['status'] == 'interview':
                interview_date = timezone.now() + timedelta(days=random.randint(1, 7))
                Interview.objects.create(
                    application=application,
                    scheduled_date=interview_date,
                    interview_type=random.choice(['phone', 'video', 'onsite']),
                    duration=random.choice([30, 45, 60]),
                    meeting_link='https://meet.google.com/abc-defg-hij' if random.choice([True, False]) else '',
                    location='Remote' if random.choice([True, False]) else 'Office',
                    status='scheduled',
                    feedback='',
                    rating=None
                )
                application.interview_scheduled = interview_date
                application.save()
            
            # Add offer if status is offer
            if candidate['status'] == 'offer':
                application.offer_made = True
                application.offer_date = timezone.now() - timedelta(days=random.randint(1, 3))
                application.offer_details = {
                    'salary': 80000 + i * 10000,
                    'bonus': 5000,
                    'start_date': (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
                    'benefits': ['Health Insurance', '401k', 'Flexible Hours']
                }
                application.save()
            
            # Add notes
            note_count = random.randint(1, 3)
            for n in range(note_count):
                ApplicationNote.objects.create(
                    application=application,
                    recruiter=recruiters[0],
                    note=random.choice([
                        f'Phone screening went well. Candidate demonstrated good knowledge of {candidate["skills"][0] if candidate["skills"] else "relevant skills"}.',
                        'Follow up scheduled for next week.',
                        'Need to check references.',
                        'Impressive portfolio and previous work experience.',
                        'Good communication skills during initial interview.',
                        'Requires technical assessment.',
                        'Strong cultural fit with team.'
                    ]),
                    is_private=random.choice([True, False])
                )
            
            # Add tags
            tag_colors = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EF4444']
            possible_tags = ['Technical', 'Culture Fit', 'High Potential', 'Needs Review', 'Urgent', 'Remote', 'Senior']
            
            for tag in random.sample(possible_tags, random.randint(1, 3)):
                CandidateTag.objects.create(
                    application=application,
                    tag=tag,
                    color=random.choice(tag_colors),
                    created_by=recruiters[0]
                )
            
            # Add communications
            comm_count = random.randint(2, 5)
            for c in range(comm_count):
                comm_date = application.applied_at + timedelta(days=c)
                CandidateCommunication.objects.create(
                    application=application,
                    recruiter=recruiters[0],
                    communication_type=random.choice(['email', 'call', 'message']),
                    subject=random.choice([
                        f'Regarding your application for {candidate["position"]}',
                        'Interview Invitation',
                        'Application Update',
                        'Reference Check',
                        'Offer Letter'
                    ]),
                    content=random.choice([
                        f'Hi {candidate["name"]}, thank you for applying to our {candidate["position"]} position.',
                        'We would like to schedule an interview with you.',
                        'We need additional information for your application.',
                        'Congratulations! We are pleased to extend an offer.',
                        'Thank you for your interest in our company.'
                    ]),
                    sent_at=comm_date,
                    is_outgoing=random.choice([True, False]),
                    attachments=[]
                )
            
            self.stdout.write(f'Created application for {candidate["name"]}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(dummy_candidates)} dummy applications!'))