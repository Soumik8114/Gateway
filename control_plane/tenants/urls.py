from django.urls import path
from . import views

urlpatterns = [
    path("", views.tenant_dashboard, name="tenant-dashboard"),
    path("api/create/", views.create_api, name="create-api"),
    path("key/create/", views.create_api_key, name="create-api-key"),
]
