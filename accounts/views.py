from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .models import UserProfile
from .forms import CustomUserCreationForm, UserProfileForm
from django.contrib.auth.models import User


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Создаем профиль для пользователя
            UserProfile.objects.create(
                user=user,
                role='student'
            )
            login(request, user)
            messages.success(request, 'Регистрация успешна! Пожалуйста, заполните информацию о себе.')
            return redirect('complete_profile')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Проверяем, есть ли профиль у пользователя
            if not hasattr(user, 'profile'):
                # Создаем профиль, если его нет
                UserProfile.objects.create(
                    user=user,
                    role='admin' if user.is_superuser else 'student'
                )
            login(request, user)

            # Если профиль не заполнен, перенаправляем на страницу заполнения
            if not user.profile.is_profile_complete() and user.profile.role == 'student':
                messages.warning(request, 'Пожалуйста, заполните информацию о себе перед созданием заявок.')
                return redirect('complete_profile')

            return redirect('home')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    return render(request, 'registration/login.html')


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


@login_required
def complete_profile_view(request):
    """Страница заполнения профиля"""
    # Проверяем, есть ли уже заполненный профиль
    if request.user.profile.is_profile_complete():
        messages.info(request, 'Ваш профиль уже заполнен.')
        return redirect('home')

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            profile = form.save(commit=False)
            # Обновляем полное имя в модели User
            full_name = form.cleaned_data['full_name']
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                request.user.first_name = name_parts[0]
                request.user.last_name = ' '.join(name_parts[1:])
            else:
                request.user.first_name = full_name
                request.user.last_name = ''
            request.user.save()
            profile.save()
            messages.success(request, 'Профиль успешно заполнен! Теперь вы можете создавать заявки.')
            return redirect('home')
    else:
        form = UserProfileForm(instance=request.user.profile)

    return render(request, 'accounts/complete_profile.html', {'form': form})