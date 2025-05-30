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

def test_lecturer_grades_display_students(self):
        response = self.client.get(reverse('education:lecturer_grades'), {
            'discipline': self.discipline1.id,
            'group': self.group.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)

def test_save_grades(self):
        response = self.client.post(reverse('education:save_grades'), {
            'discipline': self.discipline1.id,
            'group': self.group.id,
            f'semester_grade_{self.student.id}': '40',
            f'exam_grade_{self.student.id}': '30',
        })
        self.assertEqual(response.status_code, 302)
        grade = Grade.objects.get(student=self.student, exam__course=self.course)
        self.assertEqual(float(grade.grade_value), 70.0)

def test_grade_model_validation(self):
        grade = Grade(
            student=self.student,
            exam=self.exam,
            teacher=self.lecturer,
            grade_value=50  # Below minimum
        )
        with self.assertRaises(ValidationError):
            grade.full_clean()
            
def test_exam_type_based_on_semester(self):
        # First request with discipline1 (should use self.exam with type='credit')
        response = self.client.get(reverse('education:lecturer_grades'), {
            'discipline': self.discipline1.id,  # Explicitly use discipline1
            'group': self.group.id
        })
        self.assertEqual(response.status_code, 200)
        student = response.context['students'][0]
        self.assertEqual(student.exam_type, 'credit')

        # Second request with discipline2 (should use exam2 with type='exam')
        exam2 = Exam.objects.create(course=self.course2, date=timezone.now(), type='exam')
        response = self.client.get(reverse('education:lecturer_grades'), {
            'discipline': self.discipline2.id,  # Switch to discipline2
            'group': self.group.id
        })
        self.assertEqual(response.status_code, 200)
        student = response.context['students'][0]
        self.assertEqual(student.exam_type, 'exam')
    
def test_full_grade_submission_flow(self):
        response = self.client.get(reverse('education:lecturer_grades'), {
            'discipline': self.discipline1.id,
            'group': self.group.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)

        response = self.client.post(reverse('education:save_grades'), {
            'discipline': self.discipline1.id,
            'group': self.group.id,
            f'semester_grade_{self.student.id}': '50',
            f'exam_grade_{self.student.id}': '40',
        })
        self.assertEqual(response.status_code, 302)

        grade = Grade.objects.get(student=self.student, exam__course=self.course)
        self.assertEqual(float(grade.grade_value), 90.0)

        response = self.client.get(reverse('education:lecturer_grades'), {
            'discipline': self.discipline1.id,
            'group': self.group.id
        })
        self.assertContains(response, '90')  # Check total grade instead

def test_reset_dropdowns_on_cancel(self):
        response = self.client.get(reverse('education:lecturer_grades'), {
            'discipline': self.discipline1.id,
            'group': self.group.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)

        response = self.client.get(reverse('education:lecturer_grades'), {
            'discipline': '',
            'group': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Оберіть дисципліну та групу для відображення студентів.')
