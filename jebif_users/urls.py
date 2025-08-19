from django.urls import path
from .views import RegisterView
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='jebif_users/login.html'), name='login'),
    path('logout/', views.logout, name='logout'),
    path('button_logout/', views.logout, name='button_logout'),
    path('register/', RegisterView.as_view(), name='register'),
]