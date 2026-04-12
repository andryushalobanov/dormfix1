from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('complete/', views.complete_profile_view, name='complete_profile'),
]