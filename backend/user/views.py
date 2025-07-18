
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.views import View
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomLoginForm
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

class HomeView(View):
    @method_decorator(login_required)
    def get(self, request):
        context = {
            'user': request.user,
            'role': request.user.role.name if request.user.role else None
        }
        return render(request, 'user/user.html', context)



from django.views.decorators.csrf import csrf_protect

@csrf_protect
def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # Make sure this matches your form field
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.full_name}!')
                return redirect('dossier_list')
            else:
                messages.error(request, 'Authentication failed.')
        else:
            messages.error(request, 'Invalid form submission.')
    else:
        form = CustomLoginForm(request)  # Pass request to form initialization
    
   
    return render(request, 'auth/login.html', {'form': form})
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')