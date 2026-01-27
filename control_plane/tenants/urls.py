from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.tenant_login, name="tenant-login"),
    path("logout/", views.tenant_logout, name="tenant-logout"),
    path("", views.tenant_dashboard, name="tenant-dashboard"),
]
