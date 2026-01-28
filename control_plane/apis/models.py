from django.db import models
from tenants.models import Tenant
import hashlib
import secrets
from billing.models import Plan

class API(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    upstream_base_url = models.URLField()
    auth_header_name = models.CharField(max_length=100, default='X-API-Key')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "slug")

    def __str__(self):
        return f"{self.tenant.slug}/{self.slug}"

class APIKey(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    hashed_key = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_key():
        raw_key = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, hashed

    def __str__(self):
        return f"APIKey({self.tenant.slug})"

class Client(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    client_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.slug} - {self.name} ({self.client_id})"
