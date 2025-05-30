from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class ApplicationUser(AbstractUser):
    full_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username

class Faculty(models.Model):
    name = models.CharField(max_length=255, unique=True)
    dean_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)  # Added description field
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=50)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"

class Student(models.Model):
    user = models.OneToOneField(ApplicationUser, on_delete=models.CASCADE, related_name='student')
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    study_year = models.CharField(max_length=20, default="2023-2024")
    created_by_admin_id = models.CharField(max_length=50, default="Pending")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

class Teacher(models.Model):
    user = models.OneToOneField(ApplicationUser, on_delete=models.CASCADE, related_name='teacher')
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    degree = models.CharField(max_length=100)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    created_by_admin_id = models.CharField(max_length=50, default="Pending")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

class Discipline(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    hours = models.IntegerField()
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    @property
    def credits(self):
        return int(self.hours / 30)

    def __str__(self):
        return self.name

class Course(models.Model):
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    study_year = models.CharField(max_length=20)
    semester = models.IntegerField(choices=[(1, 'First'), (2, 'Second')])  # Limited to two semesters
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.discipline.name} - {self.teacher.full_name}"

class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateTimeField()
    type = models.CharField(max_length=20, choices=[('exam', 'Exam'), ('credit', 'Credit')], default='exam')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course} - {self.date}"

class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    grade_value = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(60), MaxValueValidator(100)])  # Updated min to 60
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.exam.course.discipline.name}, {self.student.group.name}, {self.student.full_name}, {self.grade_value}"

class PendingRegistration(models.Model):
    user = models.OneToOneField(ApplicationUser, on_delete=models.CASCADE)
    requested_faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True)
    requested_group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    requested_degree = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.status}"