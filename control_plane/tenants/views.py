from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.text import slugify
import json

from apis.models import API, APIKey
from billing.models import Plan
from tenants.models import Tenant


def _is_ajax(request) -> bool:
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _parse_json_body(request) -> dict:
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        raise ValidationError('Invalid JSON')


def _get_field(request, name: str) -> str:
    if request.headers.get('content-type', '').startswith('application/json'):
        data = _parse_json_body(request)
        return (data.get(name) or '').strip()
    return (request.POST.get(name) or '').strip()


def _get_int_field(request, name: str):
    raw = _get_field(request, name)
    if raw == '':
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer")

def home_view(request):
    return render(request, "tenants/home.html")


@ensure_csrf_cookie
def register_view(request):
    if request.user.is_authenticated:
        return redirect('tenant-dashboard')

    if request.method == 'POST':
        try:
            username = _get_field(request, 'username')
            email = _get_field(request, 'email')
            tenant_name = _get_field(request, 'tenant_name')
            password = _get_field(request, 'password')
            confirm_password = _get_field(request, 'confirm_password')

            errors = {}
            if not username:
                errors['username'] = 'Username is required.'
            if not tenant_name:
                errors['tenant_name'] = 'Tenant name is required.'
            if not password:
                errors['password'] = 'Password is required.'
            if password and confirm_password and password != confirm_password:
                errors['confirm_password'] = 'Passwords do not match.'

            tenant_slug = slugify(tenant_name) if tenant_name else ''
            if tenant_slug and Tenant.objects.filter(slug=tenant_slug).exists():
                errors['tenant_name'] = 'Tenant with this name already exists (slug conflict).'

            if username and User.objects.filter(username=username).exists():
                errors['username'] = 'This username is already taken.'

            if errors:
                if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
                    return JsonResponse({'success': False, 'errors': errors}, status=400)
                for field, msg in errors.items():
                    messages.error(request, f"{field}: {msg}")
                return render(request, "tenants/register.html")

            user = User.objects.create_user(username=username, email=email, password=password)
            Tenant.objects.create(user=user, name=tenant_name, slug=tenant_slug)
            login(request, user)

            if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
                return JsonResponse({'success': True})

            messages.success(request, "Registration successful! Welcome to your dashboard.")
            return redirect('tenant-dashboard')
        except ValidationError as e:
            if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            messages.error(request, str(e))

    return render(request, "tenants/register.html")


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')

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

    context = {
        'tenant': tenant,
        'apis': apis,
        'api_keys': api_keys,
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

    # Legacy page: keep rendering, but API registration now happens via dashboard HTML+JS.
    context = {
        'tenant': tenant,
        'fastapi_base_url': 'http://localhost:7000',
    }
    return render(request, "tenants/register_api.html", context)

@login_required
@require_POST
def create_api(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
         return redirect('tenant-dashboard')

    try:
        name = _get_field(request, 'name')
        slug = _get_field(request, 'slug')
        upstream_base_url = _get_field(request, 'upstream_base_url')
        auth_header_name = _get_field(request, 'auth_header_name') or 'X-API-Key'

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not slug:
            errors['slug'] = 'Slug is required.'
        if not upstream_base_url:
            errors['upstream_base_url'] = 'Upstream base URL is required.'

        if upstream_base_url:
            try:
                URLValidator()(upstream_base_url)
            except ValidationError:
                errors['upstream_base_url'] = 'Enter a valid URL.'

        if slug and API.objects.filter(tenant=tenant, slug=slug).exists():
            errors['slug'] = 'An API with this slug already exists.'

        if errors:
            if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            for field, msg in errors.items():
                messages.error(request, f"{field}: {msg}")
            return redirect('tenant-dashboard')

        try:
            api = API.objects.create(
                tenant=tenant,
                name=name,
                slug=slug,
                upstream_base_url=upstream_base_url,
                auth_header_name=auth_header_name,
                is_active=True,
            )
        except IntegrityError:
            if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
                return JsonResponse({'success': False, 'errors': {'slug': 'An API with this slug already exists.'}}, status=400)
            messages.error(request, 'slug: An API with this slug already exists.')
            return redirect('tenant-dashboard')

        success_message = f"API '{api.name}' created successfully."
        if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
            return JsonResponse({'success': True, 'message': success_message})
        messages.success(request, success_message)
        return redirect('tenant-dashboard')
    except ValidationError as e:
        if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('tenant-dashboard')

@login_required
@require_POST
def create_api_key(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
         return redirect('tenant-dashboard')

    try:
        plan_name = _get_field(request, 'plan_name')
        rpm = _get_int_field(request, 'requests_per_minute')
        rpmth = _get_int_field(request, 'requests_per_month')

        errors = {}
        if not plan_name:
            errors['plan_name'] = 'Plan name is required.'
        if rpm is None or rpm < 1:
            errors['requests_per_minute'] = 'Requests per minute must be >= 1.'
        if rpmth is None or rpmth < 1:
            errors['requests_per_month'] = 'Requests per month must be >= 1.'

        if errors:
            if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            messages.error(request, 'Failed to create API Key.')
            return redirect('tenant-dashboard')

        plan = Plan.objects.create(
            name=plan_name,
            requests_per_minute=rpm,
            requests_per_month=rpmth,
            is_active=True,
        )

        raw_key, hashed_key = APIKey.generate_key()
        APIKey.objects.create(
            tenant=tenant,
            plan=plan,
            hashed_key=hashed_key,
            is_active=True,
        )

        success_message = f"New API Key created: {raw_key} (Save this, it won't be shown again!)"
        if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
            return JsonResponse({'success': True, 'message': success_message})

        messages.success(request, success_message)
        return redirect('tenant-dashboard')
    except ValidationError as e:
        if _is_ajax(request) or request.headers.get('content-type', '').startswith('application/json'):
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('tenant-dashboard')
