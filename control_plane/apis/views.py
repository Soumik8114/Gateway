from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import APIKey,API
from tenants.models import Tenant
from billing.models import Plan

@login_required
def create_api_key(request):
    tenant = Tenant.objects.get(user=request.user)
    plan = Plan.objects.get(name="Free")  # or from POST data

    raw_key, hashed_key = APIKey.generate_key()

    APIKey.objects.create(
        tenant=tenant,
        plan=plan,
        hashed_key=hashed_key
    )

    return JsonResponse({
        "api_key": raw_key,
        "warning": "This key will be shown only once. Store it securely."
    })

@login_required
def list_apis(request):
    tenant = Tenant.objects.get(user=request.user)
    apis = API.objects.filter(tenant=tenant)

    data = [
        {
            "name": api.name,
            "slug": api.slug,
            "upstream_base_url": api.upstream_base_url
        }
        for api in apis
    ]

    return JsonResponse({"apis": data})
