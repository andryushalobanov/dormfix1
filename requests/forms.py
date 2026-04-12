from django import forms
from .models import Application, Attachment


class ApplicationForm(forms.ModelForm):
    """Форма создания заявки - соответствует твоему экрану создания заявки"""

    class Meta:
        model = Application
        fields = ['category', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Опишите проблему подробно...'
            }),
        }


class ApplicationStatusForm(forms.Form):
    """Форма изменения статуса (для мастера)"""
    status = forms.ChoiceField(
        choices=Application.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Комментарий к изменению статуса...'})
    )