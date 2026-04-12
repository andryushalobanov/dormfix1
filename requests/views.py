from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Application, Category, Attachment, StatusHistory, Notification
from .forms import ApplicationForm, ApplicationStatusForm


def is_student(user):
    return user.profile.role == 'student'


def is_maintenance(user):
    return user.profile.role == 'maintenance'


def is_admin(user):
    return user.profile.role == 'admin' or user.is_superuser


@login_required
def home(request):
    """Главная страница - дашборд в зависимости от роли"""
    if is_maintenance(request.user):
        # Мастер видит назначенные заявки
        applications = Application.objects.filter(assigned_to=request.user)
        template = 'requests/maintenance_dashboard.html'
    elif is_admin(request.user):
        # Админ видит все заявки
        applications = Application.objects.all()
        template = 'requests/admin_dashboard.html'
    else:
        # Студент видит свои заявки
        applications = Application.objects.filter(user=request.user)
        template = 'requests/student_dashboard.html'

    # Пагинация
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, template, {'applications': page_obj})


@login_required
@user_passes_test(is_student)
def create_application(request):
    """Создание заявки - по твоему wireframe"""
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()

            # Обработка фото
            files = request.FILES.getlist('photos')
            for f in files:
                Attachment.objects.create(application=application, file=f)

            # Создаем запись в истории
            StatusHistory.objects.create(
                application=application,
                status='new',
                changed_by=request.user,
                comment='Заявка создана'
            )

            # Уведомляем админов (упрощенно)
            messages.success(request, f'Заявка #{application.id} успешно создана!')
            return redirect('application_detail', application_id=application.id)
    else:
        form = ApplicationForm()

    categories = Category.objects.all()
    return render(request, 'requests/create_application.html', {
        'form': form,
        'categories': categories
    })


@login_required
def application_detail(request, application_id):
    """Детали заявки - просмотр статуса, истории, чат с мастером"""
    application = get_object_or_404(Application, id=application_id)

    # Проверка прав доступа (по твоей матрице из ПР03)
    if not (request.user == application.user or is_admin(request.user) or
            request.user == application.assigned_to):
        messages.error(request, 'У вас нет доступа к этой заявке')
        return redirect('home')

    status_history = application.status_history.all()
    attachments = application.attachments.all()
    notifications = application.notifications.filter(user=request.user)

    # Отмечаем уведомления прочитанными
    notifications.update(is_read=True)

    # Форма изменения статуса (для мастера и админа)
    status_form = None
    if is_maintenance(request.user) or is_admin(request.user):
        if request.method == 'POST' and 'change_status' in request.POST:
            status_form = ApplicationStatusForm(request.POST)
            if status_form.is_valid():
                new_status = status_form.cleaned_data['status']
                comment = status_form.cleaned_data['comment']

                # Обновляем статус
                application.status = new_status
                application.save()

                # Записываем в историю
                StatusHistory.objects.create(
                    application=application,
                    status=new_status,
                    changed_by=request.user,
                    comment=comment
                )

                # Создаем уведомление для студента
                Notification.objects.create(
                    user=application.user,
                    application=application,
                    title=f'Статус заявки #{application.id} изменен',
                    content=f'Новый статус: {application.get_status_display()}. {comment}'
                )

                messages.success(request, 'Статус заявки обновлен')
                return redirect('application_detail', application_id=application.id)
        else:
            status_form = ApplicationStatusForm(initial={'status': application.status})

    return render(request, 'requests/application_detail.html', {
        'application': application,
        'status_history': status_history,
        'attachments': attachments,
        'status_form': status_form,
    })


@login_required
@user_passes_test(is_admin)
def assign_master(request, application_id):
    """Назначение мастера на заявку - из ПР02 сценарий"""
    application = get_object_or_404(Application, id=application_id)

    if request.method == 'POST':
        master_id = request.POST.get('master_id')
        from django.contrib.auth.models import User
        master = User.objects.get(id=master_id, profile__role='maintenance')

        application.assigned_to = master
        application.save()

        StatusHistory.objects.create(
            application=application,
            status=application.status,
            changed_by=request.user,
            comment=f'Назначен мастер: {master.get_full_name()}'
        )

        Notification.objects.create(
            user=master,
            application=application,
            title='Новая заявка назначена',
            content=f'Вам назначена заявка #{application.id}: {application.description[:100]}'
        )

        messages.success(request, f'Мастер назначен на заявку #{application.id}')

    return redirect('application_detail', application_id=application.id)