from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from education.models import Teacher, Course, Discipline, Group, Student, Exam, Grade, Faculty
from django.utils import timezone

class EducationAppTests(TestCase):
    def setUp(self):
        # Set up test data using the custom user model
        self.client = Client()
        User = get_user_model()  # Dynamically get the custom user model
        # Create a user and lecturer
        self.user = User.objects.create_user(username='lecturer1', password='testpass123')
        # Create a faculty
        self.faculty = Faculty.objects.create(name='Test Faculty', dean_name='Test Dean')
        # Create a teacher (lecturer)
        self.lecturer = Teacher.objects.create(user=self.user, full_name='Test Lecturer', faculty=self.faculty,
                                               email='lecturer1@example.com', degree='PhD')
        # Create two disciplines
        self.discipline1 = Discipline.objects.create(name='Mathematics', hours=60, faculty=self.faculty)
        self.discipline2 = Discipline.objects.create(name='Physics', hours=60, faculty=self.faculty)
        # Create a course for discipline1
        self.course = Course.objects.create(
            discipline=self.discipline1,
            teacher=self.lecturer,
            study_year='2024-2025',
            semester=1,  # Credit
            start_date=timezone.now(),
            end_date=timezone.now()
        )
        # Create a course for discipline2
        self.course2 = Course.objects.create(
            discipline=self.discipline2,
            teacher=self.lecturer,
            study_year='2024-2025',
            semester=2,  # Exam
            start_date=timezone.now(),
            end_date=timezone.now()
        )
        # Create a group
        self.group = Group.objects.create(name='Group A', faculty=self.faculty)
        # Create a student
        self.student = Student.objects.create(
            user=User.objects.create_user(username='student1', password='testpass123'),
            full_name='Test Student',
            email='student1@example.com',
            group=self.group,
            faculty=self.faculty,
            study_year='2024-2025'
        )
        # Create an exam for course (discipline1)
        self.exam = Exam.objects.create(course=self.course, date=timezone.now(), type='credit')
# Log in the user
        self.client.login(username='lecturer1', password='testpass123')

    def test_lecturer_grades_view_access(self):
        response = self.client.get(reverse('education:lecturer_grades'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'education/lecturer_grades.html')

def test_lecturer_grades_view_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('education:lecturer_grades'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('education:login')}?next={reverse('education:lecturer_grades')}")
