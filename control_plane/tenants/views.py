from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.contrib import messages
import json

from .forms import APIForm, APIKeyForm
from apis.models import API, APIKey
from billing.models import Plan
from tenants.models import Tenant

@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)
        except json.JSONDecodeError:
             return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    return render(request, "tenants/login.html")

@login_required
def tenant_dashboard(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, "tenants/no_tenant.html")

    apis = API.objects.filter(tenant=tenant)
    api_keys = APIKey.objects.filter(tenant=tenant).select_related('plan')

    api_form = APIForm()
    api_key_form = APIKeyForm()

    context = {
        'tenant': tenant,
        'apis': apis,
        'api_keys': api_keys,
        'api_form': api_form,
        'api_key_form': api_key_form,
        'fastapi_base_url': 'http://localhost:8000'
    }

    return render(request, "tenants/dashboard.html", context)

@login_required
@require_POST
def create_api(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
         return redirect('tenant-dashboard')

    form = APIForm(request.POST)
    if form.is_valid():
        api = form.save(commit=False)
        api.tenant = tenant
        api.save()
        messages.success(request, f"API '{api.name}' created successfully.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect('tenant-dashboard')

@login_required
@require_POST
def create_api_key(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
         return redirect('tenant-dashboard')

    form = APIKeyForm(request.POST)
    if form.is_valid():
        plan = form.cleaned_data['plan']
        raw_key, hashed_key = APIKey.generate_key()

        APIKey.objects.create(
            tenant=tenant,
            plan=plan,
            hashed_key=hashed_key
        )

        messages.success(request, f"New API Key created: {raw_key} (Save this, it won't be shown again!)")
    else:
        messages.error(request, "Failed to create API Key.")

    return redirect('tenant-dashboard')
