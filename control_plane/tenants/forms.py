from django import forms
from apis.models import API, APIKey
from billing.models import Plan

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
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.all(),
        widget=forms.Select(attrs={'class': 'select'}),
        empty_label="Select a Plan"
    )
