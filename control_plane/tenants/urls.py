from django.urls import path
from . import views

urlpatterns = [
    path("", views.tenant_dashboard, name="tenant-dashboard"),
    path("apis/", views.my_apis, name="my-apis"),
    path("api/new/", views.register_api, name="register-api"),
    path("api/create/", views.create_api, name="create-api"),
    path("key/create/", views.create_api_key, name="create-api-key"),
]
