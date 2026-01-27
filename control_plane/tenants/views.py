from django.contrib.auth.decorators import login_required
from django.shortcuts import render

def tenant_dashboard(request):
    return render(request, "tenants/dashboard.html")
