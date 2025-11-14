from django.urls import path
from .views import RegisterView, VerifyView
from django.contrib.auth import views as auth_views
from . import views
from .views import profile_view, request_membership, admin_home_view, button_admin, test_mail

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='jebif_users/login.html'), name='login'),
    path('button_logout/', auth_views.LogoutView.as_view(next_page='home'), name='button_logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path("verify/<uid>/<token>", VerifyView.as_view(), name="verify"),
    path('profile/', profile_view, name='profile'),
    path('button_profile/', profile_view, name='button_profile'),
    path('request_membership/', request_membership, name='request_membership'),
    #ADMIN IN SITE
    path('admin/export/csv/', views.admin_export_csv, name='admin_export_csv'),
    path('button_admin/', button_admin, name='button_admin'),
    path('admin_home/', admin_home_view, name='admin_home'),
    path('admin/subscription/', views.admin_subscription, name='admin_subscription'),
    path('admin/subscription/accept/<int:info_id>/', views.admin_subscription_accept, name='admin_subscription_accept'),
    path('admin/subscription/reject/<int:info_id>/', views.admin_subscription_reject, name='admin_subscription_reject'),
    #FOR PASSWORD FORGOTTEN
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='jebif_users/password_reset.html'),name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='jebif_users/password_reset_done.html'),name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='jebif_users/password_reset_confirm.html'),name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='jebif_users/password_reset_complete.html'),name='password_reset_complete'),

    # TESTING
    path("mail/", test_mail, name="test_mail")
]