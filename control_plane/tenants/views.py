from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def tenant_login(request):
    if request.user.is_authenticated:
        return redirect("tenant-dashboard")

    next_url = request.GET.get("next", "")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        next_url = request.POST.get("next") or next_url

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if next_url and str(next_url).startswith("/"):
                return redirect(next_url)
            return redirect("tenant-dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "tenants/login.html", {"next": next_url})


def tenant_logout(request):
    logout(request)
    return redirect("tenant-login")


@login_required(login_url="tenant-login")
def tenant_dashboard(request):
    return render(request, "tenants/dashboard.html")
