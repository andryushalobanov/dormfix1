from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('maintenance', 'Мастер'),
        ('admin', 'Администратор'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    room_number = models.CharField(max_length=20, blank=True, verbose_name="Номер комнаты")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    full_name = models.CharField(max_length=100, blank=True, verbose_name="Полное имя")

    def is_profile_complete(self):
        """Проверяет, заполнен ли профиль"""
        return bool(self.full_name and self.room_number and self.phone)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"