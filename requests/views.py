from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Application, Category, Attachment, StatusHistory, Notification
from .forms import ApplicationForm, ApplicationStatusForm
from django.contrib.auth.models import User


def get_user_role(user):
    """Безопасное получение роли пользователя"""
    if hasattr(user, 'profile'):
        return user.profile.role
    return 'student'


def is_maintenance(user):
    return get_user_role(user) == 'maintenance'


def is_admin(user):
    return get_user_role(user) == 'admin' or user.is_superuser


def is_student(user):
    return get_user_role(user) == 'student'


def check_profile_complete(user):
    """Проверяет, заполнен ли профиль пользователя"""
    if is_admin(user) or is_maintenance(user):
        return True  # Админы и мастера не обязаны заполнять профиль
    return hasattr(user, 'profile') and user.profile.is_profile_complete()


@login_required
def home(request):
    """Главная страница - дашборд в зависимости от роли"""
    if is_maintenance(request.user):
        applications = Application.objects.filter(assigned_to=request.user)
        template = 'requests/maintenance_dashboard.html'
    elif is_admin(request.user):
        applications = Application.objects.all()
        template = 'requests/admin_dashboard.html'
    else:
        applications = Application.objects.filter(user=request.user)
        template = 'requests/student_dashboard.html'

    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, template, {'applications': page_obj})


@login_required
@user_passes_test(is_student)
def create_application(request):
    """Создание заявки с проверкой заполненности профиля"""
    # Проверяем, заполнен ли профиль
    if not check_profile_complete(request.user):
        messages.warning(request, 'Пожалуйста, сначала заполните информацию о себе!')
        return redirect('complete_profile')

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
    """Детали заявки - просмотр статуса, истории"""
    application = get_object_or_404(Application, id=application_id)

    # Проверка прав доступа
    if not (request.user == application.user or is_admin(request.user) or
            request.user == application.assigned_to):
        messages.error(request, 'У вас нет доступа к этой заявке')
        return redirect('home')

    status_history = application.status_history.all()
    attachments = application.attachments.all()

    # Отмечаем уведомления прочитанными
    notifications = application.notifications.filter(user=request.user)
    notifications.update(is_read=True)

    # Получаем список мастеров для назначения (только для админа)
    masters = []
    if is_admin(request.user):
        masters = User.objects.filter(profile__role='maintenance')

    # Обработка изменения статуса
    if request.method == 'POST':
        if 'change_status' in request.POST and (is_maintenance(request.user) or is_admin(request.user)):
            new_status = request.POST.get('status')
            comment = request.POST.get('comment', '')

            if new_status in dict(Application.STATUS_CHOICES):
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

    return render(request, 'requests/application_detail.html', {
        'application': application,
        'status_history': status_history,
        'attachments': attachments,
        'masters': masters,
    })


@login_required
@user_passes_test(is_admin)
def assign_master(request, application_id):
    """Назначение мастера на заявку"""
    application = get_object_or_404(Application, id=application_id)

    if request.method == 'POST':
        master_id = request.POST.get('master_id')
        if master_id:
            try:
                master = User.objects.get(id=master_id, profile__role='maintenance')
                application.assigned_to = master
                application.save()

                StatusHistory.objects.create(
                    application=application,
                    status=application.status,
                    changed_by=request.user,
                    comment=f'Назначен мастер: {master.get_full_name() or master.username}'
                )

                Notification.objects.create(
                    user=master,
                    application=application,
                    title='Новая заявка назначена',
                    content=f'Вам назначена заявка #{application.id}: {application.description[:100]}'
                )

                messages.success(request, f'Мастер назначен на заявку #{application.id}')
            except User.DoesNotExist:
                messages.error(request, 'Мастер не найден')

    return redirect('application_detail', application_id=application.id)