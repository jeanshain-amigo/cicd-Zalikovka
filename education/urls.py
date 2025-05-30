from django.urls import path
from . import views
from .views import CustomLoginView

app_name = 'education'

urlpatterns = [
    path('', views.home, name='home'),
    path('privacy/', views.privacy, name='privacy'),
    path('student/profile/', views.student_profile, name='student_profile'),
    path('student/grades/', views.student_grades, name='student_grades'),
    path('student/grades/export_pdf/', views.export_grades_pdf, name='export_grades_pdf'),
    path('lecturer/profile/', views.lecturer_profile, name='lecturer_profile'),
    path('lecturer/grades/', views.lecturer_grades, name='lecturer_grades'),
    path('lecturer/save-grades/', views.save_grades, name='save_grades'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('groups/', views.get_groups, name='get_groups'),

]
