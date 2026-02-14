from django import forms
from apis.models import API, APIKey
from django.contrib.auth.models import User
from tenants.models import Tenant
from django.core.exceptions import ValidationError
from django.utils.text import slugify

class APIForm(forms.ModelForm):
    class Meta:
        model = API
        fields = ['name', 'slug', 'upstream_base_url', 'auth_header_name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'My API'}),
            'slug': forms.TextInput(attrs={'class': 'input', 'placeholder': 'my-api'}),
            'upstream_base_url': forms.URLInput(attrs={'class': 'input', 'placeholder': 'https://api.example.com'}),
            'auth_header_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'X-API-Key'}),
        }

class APIKeyForm(forms.Form):
    plan_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Starter Plan'})
    )
    requests_per_minute = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'input', 'placeholder': '60'})
    )
    requests_per_month = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'input', 'placeholder': '10000'})
    )

class RegisterForm(forms.ModelForm):
    tenant_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'My Organization'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': '********'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': '********'})
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input', 'placeholder': 'username'}),
            'email': forms.EmailInput(attrs={'class': 'input', 'placeholder': 'user@example.com'}),
        }

    def clean_tenant_name(self):
        tenant_name = self.cleaned_data.get('tenant_name')
        if not tenant_name:
            raise ValidationError("Tenant name is required.")
        slug = slugify(tenant_name)
        if Tenant.objects.filter(slug=slug).exists():
             raise ValidationError("Tenant with this name already exists (slug conflict).")
        return tenant_name

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            Tenant.objects.create(
                user=user,
                name=self.cleaned_data['tenant_name'],
                slug=slugify(self.cleaned_data['tenant_name'])
            )
        return user
