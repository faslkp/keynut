import random
import datetime

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login as authlogin, logout as authlogout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from customers.forms import CustomerForm
from products.forms import ProductForm, CategoryForm
from products.models import Product, Category

User = get_user_model()

@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def dashboard(request):
    context = {}
    return render(request, 'admin/dashboard.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def products(request):
    context = {}
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    category = request.GET.get('category')
    q = request.GET.get('q')
    products = Product.objects.select_related('category').filter(is_deleted=False).order_by("-created_at")
    
    # Handle sort, filter, category and search
    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            products = products.order_by(Lower(field_name).desc())
        else:
            products = products.order_by(sortby)
    if filter:
        products = products.filter(is_listed = True) if filter=="listed" else products.filter(is_listed = False)
    if category:
        products = products.filter(category__slug=category)
    if q:
        products = products.filter(name__icontains=q)
    
    # Pagination
    paginator = Paginator(products, 3) #10 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    categories = Category.objects.all()
    form = ProductForm()

    context.update({'products': products, 'categories': categories, 'form': form})
    return render(request, 'admin/products.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def categories(request):
    context = {}
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')
    categories = Category.objects.all().order_by("-created_at")
    
    # Handle sort, filter, category and search
    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            categories = categories.order_by(Lower(field_name).desc())
        else:
            categories = categories.order_by(sortby)
    if filter:
        categories = categories.filter(is_deleted = False) if filter=="active" else categories.filter(is_deleted = True)
    if q:
        categories = categories.filter(name__icontains=q)
    
    # Pagination
    paginator = Paginator(categories, 3) #10 categories per page
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)

    form = CategoryForm()

    context.update({'categories': categories, 'form': form})
    return render(request, 'admin/categories.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def customers(request):
    context = {}
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')
    customers = User.objects.filter(is_staff=False).order_by("-date_joined")
    
    # Handle sort, filter and search
    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            customers = customers.order_by(Lower(field_name).desc())
        else:
            customers = customers.order_by(sortby)
    if filter:
        customers = customers.filter(is_blocked = False) if filter=="active" else customers.filter(is_blocked = True)
    if q:
        customers = customers.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    
    # Pagination
    paginator = Paginator(customers, 3) #10 customers per page
    page_number = request.GET.get('page')
    customers = paginator.get_page(page_number)

    form = CustomerForm()
    context.update({'customers': customers, 'form': form})
    return render(request, 'admin/customers.html', context=context)


@user_passes_test(lambda user: not user.is_authenticated, login_url='dashboard',redirect_field_name=None)
def admin_login(request):
    context = {}
    if request.POST:
        email = request.POST['email']
        password = request.POST['password']
        print(email, password)
        user = authenticate(username=email, password=password)
        if user and user.is_staff:
            authlogin(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Email or password is invalid!")
            context['email'] = email
    return render(request, 'admin/admin_login.html', context=context)


@user_passes_test(lambda user: not user.is_authenticated, login_url='dashboard',redirect_field_name=None)
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
            user = User.objects.filter(username=email).first()

            if user and user.is_staff:
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
                if user and user.is_staff:
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
            user = User.objects.filter(username=email).first()

            if user and user.is_staff:
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