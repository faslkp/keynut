import json

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from customers.forms import CustomerForm

User = get_user_model()


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def add_customer(request):
    if request.POST:
        form = CustomerForm(request.POST)
        print(form)
        if form.is_valid:
            user = form.save(commit=False)
            user.username = request.POST['email']
            user.set_password(request.POST['password'])
            user.save()
            return JsonResponse({
                "success": True,
                "message": f"Customer {request.POST["first_name"]} added successfully."
            })
        else:
            return JsonResponse({
                "error": True,
                "message": "Invalid data! Please verify all details."
            })
    else:
        return JsonResponse({
            "error": True,
            "message": "Invalid request!"
        })
    

@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def edit_customer(request, pk=None):
    if request.method == "POST":
        print("got post req..")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")
        user = User.objects.filter(pk=pk).first()
        if user:
            print("getting user..")
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone = phone
            if password:
                user.set_password(password)
            user.save()
            return JsonResponse({
                "success": True,
                "message": f"Customer {user.first_name} updated successfully."
            })
        else:
            return JsonResponse({
                "error": True,
                "message": "User not found!"
            })
    else:
        print("got get req..")
        user = User.objects.filter(pk=pk).first()
        if user:
            return JsonResponse({
                "first_name" : user.first_name,
                "last_name" : user.last_name,
                "email" : user.email,
                "phone" : user.phone,
            })
        else:
            return JsonResponse({
                "error": True,
                "message": "User not found!"
            })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
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
