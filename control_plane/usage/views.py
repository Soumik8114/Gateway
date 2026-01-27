from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.timezone import now
from .models import UsageDaily
from tenants.models import Tenant

@login_required
def usage_summary(request):
    tenant = Tenant.objects.get(user=request.user)
    current_month = now().date().replace(day=1)

    usage = UsageDaily.objects.filter(
        api_key__tenant=tenant,
        date__gte=current_month
    )

    total = sum(u.request_count for u in usage)

    return JsonResponse({
        "month_to_date_requests": total
    })
