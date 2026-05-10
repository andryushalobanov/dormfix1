from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('application/create/', views.create_application, name='create_application'),
    path('application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('application/<int:application_id>/assign/', views.assign_master, name='assign_master'),
]