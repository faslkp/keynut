import random
import datetime

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login as authlogin, logout as authlogout
from django.contrib import messages

User = get_user_model()


def admin_login(request):
    context = {}
    if request.POST:
        email = request.POST['email']
        password = request.POST['password']
        print(email, password)
        user = authenticate(username=email, password=password)
        if user:
            authlogin(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Email or password is invalid!")
            context['email'] = email
    return render(request, 'admin/admin_login.html', context=context)


def dashboard(request):
    context = {}
    return render(request, 'admin/dashboard.html', context=context)


def admin_recover_password(request):
    context = {
        'stage' : 'email'
    }
    if request.POST:
        email = request.POST.get('email')
        user_entered_otp = request.POST.get('otp')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 and password2 and email and password1==password2:
            print("Reseting password...")
            if User.objects.filter(username=email).exists():
                user = User.objects.get(username=email)
                user.set_password(password1)
                messages.success(request, "Password has been successfully updated.")
                return redirect('admin_login')
        elif user_entered_otp and email:
            print("Validating OTP...")

            generated_otp = request.session.get('generated_otp')
            generated_timestamp = datetime.datetime.fromisoformat(request.session.get('otp_timestamp', ''))
            
            if (datetime.datetime.now() - generated_timestamp).seconds > 300:
                print("OTP expired...")
                del request.session['generated_otp']
                generated_otp = None
            if user_entered_otp == generated_otp:
                print("OTP matching...")
                context['stage'] = 'reset'
            else:
                context['stage'] = 'otp'
                context['email'] = email
                messages.error(request, "Entered OTP is invalid or expired!")
        elif email:
            if User.objects.filter(username=email):
                print("Sending otp...")
                otp = str(random.randint(1000, 9999))
                request.session['generated_otp'] = otp
                request.session['otp_timestamp'] = str(datetime.datetime.now())
                print(otp)
                context['stage'] = 'otp'
                context['email'] = email
            else:
                messages.error(request, "Entered email is not registered with us!")
    return render(request, 'admin/admin_recover_password.html', context=context)


def admin_logout(request):
    authlogout(request)
    return redirect('admin_login')