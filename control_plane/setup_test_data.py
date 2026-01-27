import os
import django
import sys

# Setup Django environment
# Add project root to sys.path to allow importing 'control_plane', 'tenants', etc.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_plane.settings')
django.setup()

from django.contrib.auth.models import User
from tenants.models import Tenant
from apis.models import API, APIKey
from billing.models import Plan
import hashlib

def setup():
    if os.environ.get("FORCE_RESET") != "true":
        confirm = input("This will delete all Tenants, Plans, and Users. Are you sure? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    Tenant.objects.all().delete()
    Plan.objects.all().delete()
    User.objects.all().delete()
    API.objects.all().delete()
    APIKey.objects.all().delete()
    print("Deleted existing Tenants, Plans, Users, APIs, and API Keys.")
    user = User.objects.create_user(username='testuser', password='password')
    tenant = Tenant.objects.create(user=user, name='Test Tenant', slug='test-tenant')
    plan = Plan.objects.create(name='Basic Plan', requests_per_minute=5, requests_per_month=100)

    api = API.objects.create(
        tenant=tenant,
        name='Test API',
        slug='test-api',
        upstream_base_url='https://httpbin.org'
    )

    # Create API Key
    # Manual key generation to know the raw key
    raw_key = "secret_key_12345"
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

    APIKey.objects.create(
        tenant=tenant,
        plan=plan,
        hashed_key=hashed_key,
        is_active=True
    )

    print(f"Created Tenant: {tenant.slug}")
    print(f"Created API: {api.slug} -> {api.upstream_base_url}")
    print(f"Created Plan: Limit {plan.requests_per_minute} req/min")
    print(f"Created API Key: {raw_key}")

if __name__ == "__main__":
    setup()
