from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """Категория неисправности"""
    name = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Application(models.Model):
    """Заявка на ремонт"""

    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнена'),
        ('cancelled', 'Отменена'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications', verbose_name="Студент")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name="Категория")
    description = models.TextField(verbose_name="Описание проблемы")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_applications', verbose_name="Мастер",
                                    limit_choices_to={'groups__name': 'maintenance'})
    crm_lead_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="ID лида в Bitrix24"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка #{self.id} - {self.user.username}"


class Attachment(models.Model):
    """Фото к заявке"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='attachments',
                                    verbose_name="Заявка")
    file = models.ImageField(upload_to='applications/%Y/%m/%d/', verbose_name="Файл")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def __str__(self):
        return f"Фото к заявке #{self.application.id}"


class StatusHistory(models.Model):
    """История изменения статусов"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='status_history',
                                    verbose_name="Заявка")
    status = models.CharField(max_length=20, choices=Application.STATUS_CHOICES, verbose_name="Статус")
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Кто изменил")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время изменения")

    class Meta:
        verbose_name = "История статуса"
        verbose_name_plural = "История статусов"
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.application} - {self.status}"


class Notification(models.Model):
    """Уведомление"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Пользователь")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='notifications',
                                    verbose_name="Заявка")
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Содержание")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"