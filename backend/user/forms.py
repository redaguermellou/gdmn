
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'password1', 'password2')

class CustomLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")