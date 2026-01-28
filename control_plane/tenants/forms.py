from django import forms
from apis.models import API, APIKey

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
