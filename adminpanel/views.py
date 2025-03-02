import random
import datetime
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, authenticate, login as authlogin, logout as authlogout
from django.contrib import messages
from django.core.mail import send_mail
from django.http import JsonResponse

User = get_user_model()


def dashboard(request):
    context = {}
    return render(request, 'admin/dashboard.html', context=context)


def products(request):
    context = {}
    return render(request, 'admin/customers.html', context=context)


def customers(request):
    context = {}
    customers = User.objects.all()
    context.update({'customers': customers})
    return render(request, 'admin/customers.html', context=context)

def cutomer_blocking(request, pk):
    if request.method == "POST":
        try:
            user = get_object_or_404(User, pk=pk)
            print(user.first_name)
            user.is_blocked = not user.is_blocked
            user.save()
            
            # Send notification email to customer
            try:
                send_mail(
                    subject=f"Your Keynut account has been {"blocked" if user.is_blocked else "unblocked"}.",
                    message=f"Your Keynut account has been {"blocked" if user.is_blocked else "unblocked"} by administrator{" in regarding to the violation of terms and conditions. Please contact support@keynut.com for further assistance" if user.is_blocked else "."}",
                    from_email="teamkepe@gmail.com",  # Your email address
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except:
                return JsonResponse({
                    "success" : True,
                    "message" : f"Customer {user.first_name} has {"blocked" if user.is_blocked else "unblocked"} successfully. But, notification email was not sent to the customer due some technical issues."
                })

            return JsonResponse({
                "success" : True,
                "message" : f"Customer {user.first_name} has {"blocked" if user.is_blocked else "unblocked"} successfully."
            })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)


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


def admin_recover_password(request):
    context = {
        'stage' : 'email'
    }
    if request.POST:
        email = request.POST.get('email')
        user_entered_otp = request.POST.get('otp')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        resend_otp = request.POST.get('resend_otp')
        
        # Resend OTP
        if resend_otp and email:
            if User.objects.filter(username=email).exists():
                print("Resending OTP...")
                otp = str(random.randint(1000, 9999))
                request.session['generated_otp'] = otp
                request.session['otp_timestamp'] = str(datetime.datetime.now())
                context.update({'stage': 'otp', 'email': email})
                print(otp)
                try:
                    send_mail(
                        subject="Your Keynut OTP Code",
                        message=f"Your OTP is {otp}. It expires in 5 minutes.",
                        from_email="teamkepe@gmail.com",  # Your Gmail address
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    messages.success(request, "A new OTP has been sent to your email.")
                except:
                    messages.error(request, "Something went wrong while resending OTP. Please try again.")
            else:
                messages.error(request, "Entered email is not registered with us!")
                return redirect('admin_recover_password')
        
        # Validate OTP
        elif user_entered_otp and email:
            print("Validating OTP...")
            generated_otp = request.session.get('generated_otp')
            generated_timestamp = request.session.get('otp_timestamp')

            if generated_timestamp:
                generated_timestamp = datetime.datetime.fromisoformat(generated_timestamp)
                if (datetime.datetime.now() - generated_timestamp).seconds > 300:
                    print("OTP expired...")
                    del request.session['generated_otp']
                    messages.error(request, "Your OTP has expired. Please request a new one.")
                    return redirect('admin_recover_password')
            
            if user_entered_otp == generated_otp:
                print("OTP matching...")
                request.session['otp_verified'] = True
                context.update({'stage': 'reset', 'email': email})
                messages.success(request, "OTP Verified! Please enter your new password.")
            else:
                context.update({'stage': 'otp', 'email': email})
                messages.error(request, "Entered OTP is invalid or expired!")
        
        # Reset password
        elif password1 and password2 and email and request.session.get('otp_verified'):
            if password1 == password2:
                print("Reseting password...")
                user = User.objects.filter(username=email).first()
                if user:
                    user.set_password(password1)
                    user.save()
                    del request.session['otp_verified']
                    messages.success(request, "Password has been successfully updated.")
                    return redirect('admin_login')
                else:
                    messages.error(request, "User not found.")
            else:
                messages.error(request, "Passwords do not match.")
                context.update({'stage': 'reset', 'email': email})
        
        # Sendig OTP
        elif email:
            if User.objects.filter(username=email):
                print("Sending otp...")
                otp = str(random.randint(1000, 9999))
                request.session['generated_otp'] = otp
                request.session['otp_timestamp'] = str(datetime.datetime.now())
                context.update({'stage': 'otp', 'email': email})
                print(otp)
                try:
                    send_mail(
                        subject="Your Keynut OTP Code",
                        message=f"Your OTP is {otp}. It expires in 5 minutes.",
                        from_email="teamkepe@gmail.com",  # Your Gmail address
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    messages.success(request, "OTP has been sent to your email.")
                except:
                    messages.error(request, "Something went wrong while sending OTP. Please try again.")
            else:
                messages.error(request, "Entered email is not registered with us!")
    
    return render(request, 'admin/admin_recover_password.html', context=context)


def admin_logout(request):
    authlogout(request)
    return redirect('admin_login')