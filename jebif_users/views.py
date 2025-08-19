from django.shortcuts import render, redirect
from django.views import View
from .forms import UserRegisterForm
from django.contrib.auth.views import LogoutView, LoginView

class RegisterView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, 'jebif_users/register.html', {'form': form})

    def post(self, request):
        form = UserRegisterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('home')
        else:
            return render(request, 'jebif_users/register.html', {'form': form})

def logout(request):
    if request.method == 'POST':
        return LogoutView.as_view(next_page='login')(request)
    else:
        return render(request, 'jebif_users/logout.html')
    

def login(request):
    if request.method == 'POST':
        return LoginView.as_view(next_page='home')(request)
    else:
        return render(request, 'jebif_users/login.html')