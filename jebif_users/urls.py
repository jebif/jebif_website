from django.urls import path
from .views import RegisterView
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from . import views
from .views import profile_view, request_membership

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='jebif_users/login.html'), name='login'),
    path('logout/', views.logout, name='logout'),
    path('button_logout/', views.logout, name='button_logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', profile_view, name='profile'),
    path('button_profile/', profile_view, name='button_profile'),
    path('request_membership/', request_membership, name="request_membership"),
    #path('subscription/', views.subscription, name="subscription"),
    #path('subscription/ok/', TemplateView.as_view(template_name="membership/subscription-ok.html"), name="subscription_ok"),
    #path('subscription/<int:info_id>/renew/', views.subscription_renew, name="subscription_renew"),       
    # WARNING: in case info-id is not int, use re_path with regex "/(?P<info_id>\d+)/"
    #path('subscription/<int:info_id>/update/', views.subscription_update, name="subscription_update"),
    #path('subscription/me/update/', views.subscription_self_update, name="subscription_self_update"),
    #path('subscription/update/', views.subscription_preupdate, name="subscription_preupdate"),
    #path('admin/export/csv/', views.admin_export_csv, name="admin_export_csv"),
    #path('admin/subscription/', views.admin_subscription, name="admin_subscription"),
    #path('admin/subscription/accept/<int:info_id>/', views.admin_subscription_accept, name="admin_subscription_accept"),
    #path('admin/subscription/reject/<int:info_id>/', views.admin_subscription_reject, name="admin_subscription_reject"),

]