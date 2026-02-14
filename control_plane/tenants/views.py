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
    if request.user.is_authenticated:
        return redirect('tenant-dashboard')

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
        'fastapi_base_url': 'http://localhost:7000'
    }

    return render(request, "tenants/dashboard.html", context)


@login_required
def my_apis(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, "tenants/no_tenant.html")

    apis = API.objects.filter(tenant=tenant)
    context = {
        'tenant': tenant,
        'apis': apis,
        'fastapi_base_url': 'http://localhost:7000',
    }

    return render(request, "tenants/my_apis.html", context)

@login_required
def register_api(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, "tenants/no_tenant.html")

    if request.method == 'POST':
        form = APIForm(request.POST)
        if form.is_valid():
            api = form.save(commit=False)
            api.tenant = tenant
            api.save()
            messages.success(request, f"API '{api.name}' created successfully.")
            return redirect('tenant-dashboard')

        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    else:
        form = APIForm()

    context = {
        'tenant': tenant,
        'api_form': form,
    }

    return render(request, "tenants/register_api.html", context)

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
        plan = Plan.objects.create(
            name=form.cleaned_data['plan_name'],
            requests_per_minute=form.cleaned_data['requests_per_minute'],
            requests_per_month=form.cleaned_data['requests_per_month'],
            is_active=True
        )
        raw_key, hashed_key = APIKey.generate_key()

        APIKey.objects.create(
            tenant=tenant,
            plan=plan,
            hashed_key=hashed_key
        )
        success_message = f"New API Key created: {raw_key} (Save this, it won't be shown again!)"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': success_message})

        messages.success(request, success_message)
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        messages.error(request, "Failed to create API Key.")

    return redirect('tenant-dashboard')
