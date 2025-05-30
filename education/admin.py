from django.contrib import admin
from .models import ApplicationUser, Faculty, Group, Student, Teacher, Discipline, Course, Exam, Grade, PendingRegistration

admin.site.register(ApplicationUser)
admin.site.register(Faculty)
admin.site.register(Group)
admin.site.register(Student)
admin.site.register(Teacher)
admin.site.register(Discipline)
admin.site.register(Course)
admin.site.register(Exam)
admin.site.register(Grade)
admin.site.register(PendingRegistration)