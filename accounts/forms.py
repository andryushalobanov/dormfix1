from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    full_name = forms.CharField(max_length=100, required=True, label="Полное имя")
    room_number = forms.CharField(max_length=20, required=True, label="Номер комнаты")
    phone = forms.CharField(max_length=20, required=True, label="Номер телефона")

    class Meta:
        model = UserProfile
        fields = ['full_name', 'room_number', 'phone']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '101'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['full_name'].initial = self.instance.user.get_full_name()