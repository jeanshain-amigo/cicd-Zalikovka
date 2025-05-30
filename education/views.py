from django.contrib.auth.views import LoginView
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse_lazy
from collections import defaultdict

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

from .models import ApplicationUser, Student, Teacher, Faculty, Group, Grade, PendingRegistration, Course, Exam
from django.contrib import messages
from django.db.models import Avg, Count, Q, Max, Min
from datetime import datetime, timezone

User = get_user_model()

# Role checks
def is_student(user):
    return hasattr(user, 'student') and user.is_active

def is_teacher(user):
    return hasattr(user, 'teacher') and user.is_active

class CustomLoginView(LoginView):
    template_name = 'education/login.html'
    success_url = reverse_lazy('education:student_profile')  # Redirect to student profile after login
    redirect_authenticated_user = True  # Redirect if already logged in

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '')  # Preserve next parameter for redirect
        return context

    def form_valid(self, form):
        # Handle "Remember me" checkbox to set session expiration
        if not self.request.POST.get('remember'):
            self.request.session.set_expiry(0)  # Session expires when browser closes
        else:
            self.request.session.set_expiry(1209600)  # 2 weeks (default Django session length)
        return super().form_valid(form)

# Views
def home(request):
    return render(request, 'education/home.html')

def privacy(request):
    return render(request, 'education/privacy.html')

@login_required
@user_passes_test(is_student, login_url='education:home')
def student_profile(request):
    student = request.user.student
    grades = Grade.objects.filter(student=student).order_by('exam__date')

    # Calculate statistics for all grades
    average_grade = grades.aggregate(Avg('grade_value'))['grade_value__avg'] or 0
    highest_grade = grades.aggregate(Max('grade_value'))['grade_value__max']
    lowest_grade = grades.aggregate(Min('grade_value'))['grade_value__min']

    # Get highest and lowest grade exams for display
    highest_grade_exam = grades.filter(grade_value=highest_grade).first() if highest_grade else None
    lowest_grade_exam = grades.filter(grade_value=lowest_grade).first() if lowest_grade else None

    # Total subjects, exams, and credits
    total_disciplines = grades.count()
    exams = grades.filter(exam__type='exam').count()
    credits = grades.filter(exam__type='credit').count()

    # Calculate current academic year based on date
    current_date = datetime.now()
    current_year = current_date.year
    if current_date.month < 9:  # Before September, use previous year for academic year start
        current_academic_year = f"{current_year - 1}-{str(current_year)[-2:]}"
    else:
        current_academic_year = f"{current_year}-{str(current_year + 1)[-2:]}"

    # Use student's study_year as the starting academic year
    study_start_year = student.study_year  # e.g., "2023-2024"

    # Calculate study year (number of years completed)
    start_year = int(study_start_year.split('-')[0])
    current_start_year = int(current_academic_year.split('-')[0])
    study_year = current_start_year - start_year + 1

    # Round average grade
    average_grade = round(average_grade) if average_grade else 0

    context = {
        'student': student,
        'grades': grades,
        'average_grade': average_grade,
        'highest_grade_exam': highest_grade_exam,
        'lowest_grade_exam': lowest_grade_exam,
        'total_disciplines': total_disciplines,
        'exams': exams,
        'credits': credits,
        'study_year': study_year,
    }
    return render(request, 'education/student_profile.html', context)

@login_required
@user_passes_test(is_student, login_url='education:home')
def student_grades(request):
    student = request.user.student
    grades = Grade.objects.filter(student=student)

    # Calculate student's current study year
    current_date = datetime.now()
    current_year = current_date.year
    if current_date.month < 9:
        current_academic_year = f"{current_year - 1}-{str(current_year)[-2:]}"
    else:
        current_academic_year = f"{current_year}-{str(current_year + 1)[-2:]}"
    study_start_year = student.study_year
    start_year = int(study_start_year.split('-')[0])
    current_start_year = int(current_academic_year.split('-')[0])
    student_study_year = current_start_year - start_year + 1

    # Apply filters
    grade_min = int(request.GET.get('grade_min', 60))
    grade_max = int(request.GET.get('grade_max', 100))
    course_min = int(request.GET.get('course_min', 1))
    course_max = int(request.GET.get('course_max', 6))
    semester_1 = request.GET.get('semester_1') == 'on'
    semester_2 = request.GET.get('semester_2') == 'on'
    type_exam = request.GET.get('type_exam') == 'on'
    type_credit = request.GET.get('type_credit') == 'on'
    sort_type = request.GET.get('sort_type', 'seq')

    # Filter by grade range
    grades = grades.filter(grade_value__gte=grade_min, grade_value__lte=grade_max)

    # Filter by course year and group by academic year, semester, and type
    grades_by_year = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    filtered_grades = []
    for grade in grades:
        exam_year = grade.exam.date.year
        if grade.exam.date.month >= 9:
            academic_year = f"{exam_year}-{str(exam_year + 1)[-2:]}"
        else:
            academic_year = f"{exam_year - 1}-{str(exam_year)[-2:]}"
        grade.academic_year = academic_year
        study_year = int(academic_year.split('-')[0]) - start_year + 1
        if course_min <= study_year <= course_max:
            filtered_grades.append(grade)
            semester = grade.exam.course.semester
            semester_name = "I" if semester == 1 else "II"
            grades_by_year[academic_year][semester_name][grade.exam.type].append(grade)

    # Apply semester filter
    if semester_1 and not semester_2:
        grades_by_year = {
            year: {sem: types for sem, types in semesters.items() if sem == "I"}
            for year, semesters in grades_by_year.items()
        }
    elif semester_2 and not semester_1:
        grades_by_year = {
            year: {sem: types for sem, types in semesters.items() if sem == "II"}
            for year, semesters in grades_by_year.items()
        }
    elif not semester_1 and not semester_2:
        semester_1 = True
        semester_2 = True

    # Apply discipline type filter
    if type_exam and not type_credit:
        grades_by_year = {
            year: {sem: {typ: grades for typ, grades in types.items() if typ == 'exam'}
                   for sem, types in semesters.items()}
            for year, semesters in grades_by_year.items()
        }
    elif type_credit and not type_exam:
        grades_by_year = {
            year: {sem: {typ: grades for typ, grades in types.items() if typ == 'credit'}
                   for sem, types in semesters.items()}
            for year, semesters in grades_by_year.items()
        }
    elif not type_exam and not type_credit:
        type_exam = True
        type_credit = True

    # Apply sorting within each group
    for academic_year in grades_by_year:
        for semester in grades_by_year[academic_year]:
            for exam_type in grades_by_year[academic_year][semester]:
                grades_list = grades_by_year[academic_year][semester][exam_type]
                if sort_type == 'asc':
                    grades_list.sort(key=lambda g: g.grade_value)
                elif sort_type == 'desc':
                    grades_list.sort(key=lambda g: g.grade_value, reverse=True)
                else:  # 'seq'
                    grades_list.sort(key=lambda g: (g.exam.date, g.exam.course.discipline.name))

    # Convert to template-friendly structure with chronological order and preserved sorting
    grouped_grades = []
    sorted_years = sorted(grades_by_year.keys(), key=lambda x: [int(y) for y in x.split('-')])
    for academic_year in sorted_years:
        semester_list = []
        semester_groups = grades_by_year[academic_year]
        for semester in sorted(semester_groups.keys(), key=lambda x: {'I': 1, 'II': 2}[x]):
            type_list = []
            for exam_type, grades in semester_groups[semester].items():
                if grades:  # Only include non-empty groups
                    # Reapply sorting to ensure it’s preserved
                    if sort_type == 'asc':
                        grades.sort(key=lambda g: g.grade_value)
                    elif sort_type == 'desc':
                        grades.sort(key=lambda g: g.grade_value, reverse=True)
                    else:  # 'seq'
                        grades.sort(key=lambda g: (g.exam.date, g.exam.course.discipline.name))
                    type_list.append((exam_type, grades))
            if type_list:  # Only include semesters with grades
                semester_list.append((semester, type_list))
        if semester_list:  # Only include years with grades
            grouped_grades.append((academic_year, semester_list))

    # Calculate statistics on filtered grades
    filtered_grades_qs = Grade.objects.filter(
        id__in=[g.id for g in filtered_grades]
    )
    average_grade = filtered_grades_qs.aggregate(Avg('grade_value'))['grade_value__avg'] or 0
    highest_grade = filtered_grades_qs.aggregate(Max('grade_value'))['grade_value__max']
    lowest_grade = filtered_grades_qs.aggregate(Min('grade_value'))['grade_value__min']
    highest_grade_exam = filtered_grades_qs.filter(grade_value=highest_grade).first() if highest_grade else None
    lowest_grade_exam = filtered_grades_qs.filter(grade_value=lowest_grade).first() if lowest_grade else None
    total_disciplines = filtered_grades_qs.count()
    exams = filtered_grades_qs.filter(exam__type='exam').count()
    credits = filtered_grades_qs.filter(exam__type='credit').count()

    print(f"Sort type: {sort_type}, Grouped grades: {grouped_grades}")

    context = {
        'student': student,
        'grouped_grades': grouped_grades,
        'average_grade': round(average_grade) if average_grade else 0,
        'highest_grade_exam': highest_grade_exam,
        'lowest_grade_exam': lowest_grade_exam,
        'total_disciplines': total_disciplines,
        'exams': exams,
        'credits': credits,
        'grade_min': grade_min,
        'grade_max': grade_max,
        'course_min': course_min,
        'course_max': course_max,
        'semester_1': semester_1,
        'semester_2': semester_2,
        'type_exam': type_exam,
        'type_credit': type_credit,
        'sort_type': sort_type,
    }
    return render(request, 'education/student_grades.html', context)

@login_required
@user_passes_test(is_student, login_url='education:home')
def export_grades_pdf(request):
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    student = request.user.student
    grades = Grade.objects.filter(student=student)

    # Apply the same filters as in student_grades view
    grade_min = int(request.POST.get('grade_min', 60))
    grade_max = int(request.POST.get('grade_max', 100))
    course_min = int(request.POST.get('course_min', 1))
    course_max = int(request.POST.get('course_max', 6))
    semester_1 = request.POST.get('semester_1') == 'on'
    semester_2 = request.POST.get('semester_2') == 'on'
    type_exam = request.POST.get('type_exam') == 'on'
    type_credit = request.POST.get('type_credit') == 'on'
    sort_type = request.POST.get('sort_type', 'seq')

    # Calculate student's current study year
    current_date = datetime.now()
    current_year = current_date.year
    if current_date.month < 9:
        current_academic_year = f"{current_year - 1}-{str(current_year)[-2:]}"
    else:
        current_academic_year = f"{current_year}-{str(current_year + 1)[-2:]}"
    study_start_year = student.study_year
    start_year = int(study_start_year.split('-')[0])
    current_start_year = int(current_academic_year.split('-')[0])
    student_study_year = current_start_year - start_year + 1

    # Apply filters
    grades = grades.filter(grade_value__gte=grade_min, grade_value__lte=grade_max)
    grades_by_year = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    filtered_grades = []
    for grade in grades:
        exam_year = grade.exam.date.year
        if grade.exam.date.month >= 9:
            academic_year = f"{exam_year}-{str(exam_year + 1)[-2:]}"
        else:
            academic_year = f"{exam_year - 1}-{str(exam_year)[-2:]}"
        grade.academic_year = academic_year
        study_year = int(academic_year.split('-')[0]) - start_year + 1
        if course_min <= study_year <= course_max:
            filtered_grades.append(grade)
            semester = grade.exam.course.semester  # Assuming semester is stored in Course model
            semester_name = "I" if semester == 1 else "II"
            grades_by_year[academic_year][semester_name][grade.exam.type].append(grade)

    # Apply semester filter
    if semester_1 and not semester_2:
        grades_by_year = {
            year: {sem: types for sem, types in semesters.items() if sem == "I"}
            for year, semesters in grades_by_year.items()
        }
    elif semester_2 and not semester_1:
        grades_by_year = {
            year: {sem: types for sem, types in semesters.items() if sem == "II"}
            for year, semesters in grades_by_year.items()
        }

    # Apply discipline type filter
    if type_exam and not type_credit:
        grades_by_year = {
            year: {sem: {typ: grades for typ, grades in types.items() if typ == 'exam'}
                   for sem, types in semesters.items()}
            for year, semesters in grades_by_year.items()
        }
    elif type_credit and not type_exam:
        grades_by_year = {
            year: {sem: {typ: grades for typ, grades in types.items() if typ == 'credit'}
                   for sem, types in semesters.items()}
            for year, semesters in grades_by_year.items()
        }

    # Apply sorting
    for academic_year in grades_by_year:
        for semester in grades_by_year[academic_year]:
            for exam_type in grades_by_year[academic_year][semester]:
                grades_list = grades_by_year[academic_year][semester][exam_type]
                if sort_type == 'asc':
                    grades_list.sort(key=lambda g: g.grade_value)
                elif sort_type == 'desc':
                    grades_list.sort(key=lambda g: g.grade_value, reverse=True)
                else:
                    grades_list.sort(key=lambda g: (g.exam.date, g.exam.course.discipline.name))

    # Calculate average grade for filtered grades
    filtered_grades_qs = Grade.objects.filter(
        id__in=[g.id for g in filtered_grades]
    )
    average_grade = filtered_grades_qs.aggregate(Avg('grade_value'))['grade_value__avg'] or 0
    average_grade = round(average_grade)

    # Create PDF using reportlab
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    elements = []

    # Register DejaVuSans font for Cyrillic support
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'static/fonts/DejaVuSans.ttf'))
    except:
        # Fallback to Helvetica if font file is missing (Cyrillic won't work)
        pass

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='Title',
        fontName='DejaVuSans' if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold',
        fontSize=16,
        alignment=1,  # Center
        spaceAfter=12,
    )
    normal_style = ParagraphStyle(
        name='Normal',
        fontName='DejaVuSans' if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica',
        fontSize=12,
        alignment=1,  # Center
        spaceAfter=6,
    )

    # Add title and student details
    elements.append(Paragraph(f"Оцінки студента: {student.full_name}", title_style))
    elements.append(Paragraph(f"Факультет: {student.faculty.name}", normal_style))
    elements.append(Paragraph(f"Група: {student.group.name}", normal_style))

    # Build table data
    table_data = [["Дисципліна", "Кредити", "Години", "Оцінка", "Бали"]]
    for academic_year, semester_groups in sorted(grades_by_year.items(), reverse=True):
        for semester, type_groups in semester_groups.items():
            table_data.append([f"{semester} семестр {academic_year}", "", "", "", ""])  # Semester header
            has_data = False
            for exam_type, grades in type_groups.items():
                if grades:
                    has_data = True
                    table_data.append([("Іспити" if exam_type == 'exam' else "Заліки"), "", "", "", ""])  # Exam type header
                    for grade in grades:
                        discipline = grade.exam.course.discipline.name
                        credits = str(grade.exam.course.discipline.credits) if grade.exam.course.discipline.credits else "-"
                        hours = str(grade.exam.course.discipline.hours) if grade.exam.course.discipline.hours else "-"
                        # Apply new grading logic for assessment
                        if grade.exam.type == "credit":
                            assessment = "Зарахов."
                        else:
                            if grade.grade_value >= 90 and grade.grade_value <= 100:
                                assessment = "5"
                            elif grade.grade_value >= 75 and grade.grade_value <= 89:
                                assessment = "4"
                            elif grade.grade_value >= 60 and grade.grade_value <= 74:
                                assessment = "3"
                            else:
                                assessment = f"{grade.grade_value:.2f}"
                        points = f"{grade.grade_value:.2f}"
                        table_data.append([discipline, credits, hours, assessment, points])
            if not has_data:
                table_data.append(["(немає даних)", "", "", "", ""])  # Empty row if no data

    # Create table with text wrapping for discipline column
    from reportlab.platypus import Paragraph as PLParagraph
    col_widths = [180, 50, 50, 70, 70]  # Increased width for discipline to accommodate long names
    table_data_wrapped = []
    for row in table_data:
        wrapped_row = []
        for i, cell in enumerate(row):
            if i == 0 and isinstance(cell, str) and len(cell.split()) > 1:  # Wrap discipline names
                wrapped_row.append(PLParagraph(cell, style=normal_style))
            else:
                wrapped_row.append(cell)
        table_data_wrapped.append(wrapped_row)

    table = Table(table_data_wrapped, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans' if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Left-align discipline names
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans' if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('SPAN', (0, 1), (-1, 1)),  # Span for semester headers
    ]))

    # Adjust SPAN for semester and type headers dynamically
    row_idx = 1
    for academic_year, semester_groups in sorted(grades_by_year.items(), reverse=True):
        for semester, type_groups in semester_groups.items():
            table._argH[row_idx] = 20  # Set height for semester header
            table.setStyle(TableStyle([
                ('SPAN', (0, row_idx), (-1, row_idx)),
                ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey),
                ('FONTNAME', (0, row_idx), (-1, row_idx), 'DejaVuSans' if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'),
                ('FONTSIZE', (0, row_idx), (-1, row_idx), 12),
            ]))
            row_idx += 1
            has_data = False
            for exam_type, grades in type_groups.items():
                if grades:
                    has_data = True
                    table._argH[row_idx] = 15  # Set height for exam type header
                    table.setStyle(TableStyle([
                        ('SPAN', (0, row_idx), (-1, row_idx)),
                        ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.whitesmoke),
                        ('FONTNAME', (0, row_idx), (-1, row_idx), 'DejaVuSans' if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'),
                        ('FONTSIZE', (0, row_idx), (-1, row_idx), 10),
                    ]))
                    row_idx += 1
                    for _ in grades:
                        row_idx += 1
            if not has_data:
                row_idx += 1  # Skip an extra row for empty data

    elements.append(table)
    elements.append(Paragraph(f"Середній бал: {average_grade}", normal_style))

    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="grades_{student.full_name}.pdf"'
    response.write(pdf)
    return response

@login_required
@user_passes_test(is_teacher, login_url='education:home')
def lecturer_profile(request):
    teacher = request.user.teacher
    # Fetch all courses taught by the lecturer
    courses = Course.objects.filter(teacher=teacher).select_related('discipline')

    context = {
        'teacher': teacher,
        'courses': courses,
    }
    return render(request, 'education/lecturer_profile.html', context)

@login_required
@user_passes_test(is_teacher, login_url=reverse_lazy('login'))
def lecturer_grades(request):
    teacher = request.user.teacher
    lecturer_courses = Course.objects.filter(teacher=teacher).select_related('discipline')
    groups = Group.objects.all()

    selected_discipline_id = request.GET.get('discipline')
    selected_group_id = request.GET.get('group')
    students = []
    selected_course = None

    if selected_discipline_id and selected_group_id:
        # Ensure we get the correct course for the selected discipline
        selected_course = Course.objects.filter(
            teacher=teacher,
            discipline_id=selected_discipline_id
        ).first()
        if selected_course:
            # Get or create the exam, but don’t override the type if it already exists
            exam, created = Exam.objects.get_or_create(
                course=selected_course,
                defaults={'date': datetime.now(), 'type': 'credit' if selected_course.semester == 1 else 'exam'}
            )
            students = Student.objects.filter(group_id=selected_group_id).select_related('group')
            for student in students:
                try:
                    grade = Grade.objects.filter(
                        exam__course=selected_course,
                        student=student,
                        teacher=teacher
                    ).latest('created_at')
                    # Since we only store total_grade, split it for display
                    total_grade = float(grade.grade_value)
                    semester_grade = total_grade / 2  # Simplified split for display
                    exam_grade = total_grade / 2
                except ObjectDoesNotExist:
                    semester_grade = float(request.GET.get(f'semester_grade_{student.id}', 0))
                    exam_grade = float(request.GET.get(f'exam_grade_{student.id}', 0))
                    total_grade = min(100, semester_grade + exam_grade)

                # Use the exam’s type directly
                exam_type = exam.type

                # Assign values to student for template rendering
                student.semester_grade = semester_grade
                student.exam_grade = exam_grade
                student.total_grade = total_grade
                student.exam_type = exam_type

                # Calculate national grade
                if total_grade < 60:
                    student.national_grade = "-"
                else:
                    if exam_type == 'credit':
                        student.national_grade = "Зарахов."
                    else:  # exam
                        if total_grade >= 90:
                            student.national_grade = "5"
                        elif total_grade >= 75:
                            student.national_grade = "4"
                        else:  # 60-74
                            student.national_grade = "3"

    context = {
        'lecturer': teacher,
        'lecturer_courses': lecturer_courses,
        'groups': groups,
        'students': students,
        'selected_discipline': selected_course,
    }
    return render(request, 'education/lecturer_grades.html', context)

@login_required
@user_passes_test(is_teacher, login_url='education:home')
def save_grades(request):
    if request.method == 'POST':
        teacher = request.user.teacher
        selected_discipline_id = request.POST.get('discipline')
        selected_group_id = request.POST.get('group')
        if selected_discipline_id and selected_group_id:
            course = Course.objects.filter(teacher=teacher, discipline_id=selected_discipline_id).first()
            if course:
                # Determine exam type based on your logic (e.g., semester-based)
                exam_type = 'credit' if course.semester == 1 else 'exam'  # Adjust as needed
                exam, created = Exam.objects.get_or_create(
                    course=course,
                    defaults={'date': datetime.now(), 'type': exam_type}
                )
                students = Student.objects.filter(group_id=selected_group_id)
                for student in students:
                    semester_grade = request.POST.get(f'semester_grade_{student.id}', 0)
                    exam_grade = request.POST.get(f'exam_grade_{student.id}', 0)
                    try:
                        semester_grade = float(semester_grade)
                        exam_grade = float(exam_grade)
                        total_grade = min(100, semester_grade + exam_grade)
                        Grade.objects.update_or_create(
                            exam=exam,
                            student=student,
                            teacher=teacher,
                            defaults={'grade_value': total_grade}
                        )
                        messages.success(request, f"Оцінки для {student.full_name} збережено.")
                    except ValueError:
                        messages.error(request, f"Невірний формат оцінки для {student.full_name}.")
        else:
            messages.error(request, "Оберіть дисципліну та групу.")
    return redirect('education:lecturer_grades')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        full_name = request.POST['full_name']
        role = request.POST['role']
        faculty_id = request.POST['faculty_id']
        invite_code = request.POST.get('invite_code', '')

        # Validate role
        if role not in ['Student', 'Teacher']:
            messages.error(request, 'Invalid role.')
            return render(request, 'education/registration.html', {'faculties': Faculty.objects.all()})

        # Validate faculty
        try:
            faculty = Faculty.objects.get(id=faculty_id)
        except Faculty.DoesNotExist:
            messages.error(request, 'Invalid faculty.')
            return render(request, 'education/registration.html', {'faculties': Faculty.objects.all()})

        # Invite code logic
        auto_approve = False
        group = None
        if invite_code:
            faculty_invite = Faculty.objects.filter(invite_code=invite_code).first()
            if faculty_invite and faculty_invite.id == int(faculty_id):
                if role == 'Teacher':
                    auto_approve = True
                elif role == 'Student':
                    group = Group.objects.filter(invite_code=invite_code, faculty=faculty).first()
                    if group:
                        auto_approve = True
            if not auto_approve:
                messages.error(request, 'Invalid invite code.')
                return render(request, 'education/registration.html', {'faculties': Faculty.objects.all()})

        # Create user
        user = ApplicationUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            is_active=auto_approve
        )
        user.save()

        # Create student/teacher
        if role == 'Student':
            group_id = request.POST.get('group_id')
            if not group and not group_id:
                messages.error(request, 'Group is required for students.')
                return render(request, 'education/registration.html', {'faculties': Faculty.objects.all()})
            if not group:
                try:
                    group = Group.objects.get(id=group_id, faculty=faculty)
                except Group.DoesNotExist:
                    messages.error(request, 'Invalid group.')
                    return render(request, 'education/registration.html', {'faculties': Faculty.objects.all()})
            student = Student.objects.create(
                user=user,
                full_name=full_name,
                email=email,
                faculty=faculty,
                group=group,
                created_by_admin_id='System' if auto_approve else 'Pending'
            )
        else:
            degree = request.POST.get('degree', '')
            if not degree:
                messages.error(request, 'Degree is required for teachers.')
                return render(request, 'education/registration.html', {'faculties': Faculty.objects.all()})
            teacher = Teacher.objects.create(
                user=user,
                full_name=full_name,
                email=email,
                faculty=faculty,
                degree=degree,
                created_by_admin_id='System' if auto_approve else 'Pending'
            )

        # Handle pending registration
        if not auto_approve:
            PendingRegistration.objects.create(
                user=user,
                requested_faculty=faculty,
                requested_group=group if role == 'Student' else None,
                requested_degree=degree if role == 'Teacher' else ''
            )
            messages.success(request, 'Registration pending admin approval.')
            return redirect('education:register')

        login(request, user)  # Login the user if auto-approved
        return redirect('education:home')

    faculties = Faculty.objects.all()
    return render(request, 'education/registration.html', {'faculties': faculties})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                next_url = request.POST.get('next', 'education:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account is pending approval.')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'education/login.html')

def logout_view(request):
    logout(request)
    return redirect('education:home')

def get_groups(request):
    faculty_id = request.GET.get('faculty_id')
    groups = Group.objects.filter(faculty_id=faculty_id).values('id', 'name')
    return JsonResponse(list(groups), safe=False)