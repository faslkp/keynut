import random
import datetime

from django.shortcuts import render, redirect
from django.contrib.auth import login as authlogin, logout as authlogout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import F, Q, ExpressionWrapper, DecimalField
from django.core.mail import send_mail
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator

from products.models import Product, Category

User = get_user_model()


def index(request):
    context = {}
    categories = Category.objects.filter(is_deleted=False)
    
    flash_sales = Product.objects.filter(is_deleted=False, is_listed=True, category__is_deleted=False).annotate(
        discount_price=ExpressionWrapper(
            F('price') - (F('price') * (F('discount') / 100.0)), 
            output_field=DecimalField(max_digits=10, decimal_places=2)
            )).order_by('-relevance')[:4]
    
    best_selling = Product.objects.filter(is_deleted=False, is_listed=True, category__is_deleted=False).annotate(
        discount_price=ExpressionWrapper(
            F('price') - (F('price') * (F('discount') / 100.0)), 
            output_field=DecimalField(max_digits=10, decimal_places=2)
            ))[:4]
    
    new_arrivals = Product.objects.filter(is_deleted=False, is_listed=True, category__is_deleted=False).annotate(
        discount_price=ExpressionWrapper(
            F('price') - (F('price') * (F('discount') / 100.0)), 
            output_field=DecimalField(max_digits=10, decimal_places=2)
            )).order_by('-created_at')[:4]

    context.update({
        'categories': categories, 
        'flash_sales': flash_sales,
        'best_selling': best_selling,
        'new_arrivals': new_arrivals,
    })
    return render(request, 'web/index.html', context=context)


def products(request):
    context = {}

    q = request.GET.get('q')
    sortby = request.GET.get('sort')
    selected_categories = request.GET.getlist('category')
    selected_prices = request.GET.getlist('price')
    

    products = Product.objects.filter(is_deleted=False, is_listed=True, category__is_deleted=False).annotate(
        discount_price=ExpressionWrapper(
            F('price') - (F('price') * (F('discount') / 100.0)), 
            output_field=DecimalField(max_digits=10, decimal_places=2)
            )).order_by('-relevance')
    
    # Handle Filters
    query = Q()
    
    # Search
    if q:
        query &= Q(name__icontains=q)

    # Category selection
    if selected_categories:
        query &= Q(category__slug__in=selected_categories)
    
    # Price range
    price_filter_options = {
        'price-0-250': (0, 250),
        'price-251-500': (251, 500),
        'price-501-1000': (501, 1000),
        'price-1001-2000': (1001, 2000),
        'price-above-2000': (2001, None),
    }

    if selected_prices:
        price_query = Q()

        for key in selected_prices:
            if key in price_filter_options:
                min_price, max_price = price_filter_options[key]
                if max_price is None:
                    price_query |= Q(discount_price__gte=min_price)
                else:
                    price_query |= Q(discount_price__gte=min_price, discount_price__lte=max_price)
        query &= price_query
    
    # Apply combined filter
    products = products.filter(query)

    # Handle Sort
    sort_options = {
        'relevance': '-relevance',
        'name-a-z': 'name',
        'name-z-a': '-name',
        'price-low-high': 'discount_price',
        'price-high-low': '-discount_price',
    }

    if sortby in sort_options:
        products = products.order_by(sort_options[sortby])

    # Pagination
    paginator = Paginator(products, 3)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    categories = Category.objects.filter(is_deleted=False)
    context.update({
        'products': products,
        'categories': categories
    })
    return render(request, 'web/products.html', context=context)


def product_details(request, slug):
    context = {}
    product = Product.objects.select_related('category').filter(slug=slug).annotate(
        discount_price=ExpressionWrapper(
            F('price') - (F('price') * (F('discount') / 100.0)), 
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    ).first()
    if product and product.is_listed and not product.is_deleted and not product.category.is_deleted:
        context.update({'product': product})
    else:
        return redirect('products')
    
    # Check stock status
    lowest_variant = product.variants.order_by('quantity').first()
    is_in_stock = lowest_variant and product.stock >= lowest_variant.quantity

    related_products = Product.objects.select_related('category').filter(~Q(slug=slug)).annotate(
        discount_price=ExpressionWrapper(
            F('price') - (F('price') * (F('discount') / 100.0)), 
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    ).order_by('-relevance')[:4]
    context.update({
        'is_in_stock': is_in_stock,
        'related_products': related_products,
    })
    return render(request, 'web/product_details.html', context=context)


@never_cache
@user_passes_test(lambda user: not user.is_authenticated, login_url='/',redirect_field_name=None)
def login(request):
    context = {}

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_entered_otp = request.POST.get('otp')
        resend_otp = request.POST.get('resend_otp')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                if user.is_verified: # Check if user has verified email address
                    authlogin(request, user)
                    next = request.GET.get('next', 'index')
                    return redirect(next)
                else:
                    # If user's email is not verified
                    # Generate OTP
                    otp = str(random.randint(1000, 9999))
                    request.session['generated_otp'] = otp
                    request.session['otp_timestamp'] = str(datetime.datetime.now())
                    print(otp)

                    # Update context and session
                    context.update({
                        'stage': "otp",
                        'email': email
                    })
                    request.session['email'] = email
                    
                    # Send OTP to email
                    try:
                        send_mail(
                            subject="Your Keynut OTP Code",
                            message=f"Your OTP is {otp}. It expires in 5 minutes.",
                            from_email="teamkepe@gmail.com",  # Your email address
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        messages.error(request, "Please verify your account. An OTP has been sent to your email.")
                    except:
                        messages.error(request, "Something went wrong while sending OTP. Please click Resend OTP to send again.")
                    return render(request, 'web/register.html', context=context)
            else:
                messages.error(request, "Email and password does not match!")
        
        # Handling Resend OTP
        elif email and resend_otp:
            # Validating email
            if email == request.session['email']:
                # Generate OTP
                otp = str(random.randint(1000, 9999))
                request.session['generated_otp'] = otp
                request.session['otp_timestamp'] = str(datetime.datetime.now())
                print(otp)

                # Update context to stay on otp page
                context.update({
                    'stage': "otp",
                    'email': email
                })
                
                # Send OTP to email
                try:
                    send_mail(
                        subject="Your Keynut OTP Code",
                        message=f"Your OTP is {otp}. It expires in 5 minutes.",
                        from_email="teamkepe@gmail.com",  # Your email address
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    messages.success(request, "OTP has been sent to your email.")
                except:
                    messages.error(request, "Something went wrong while sending OTP. Please click Resend OTP to send again.")
                return render(request, 'web/register.html', context=context)
            else:
                messages.error(request, "Something went wrong! Please try again.")
                del request.session['email']
                return redirect('login')
        
        # Validating OTP
        elif email and user_entered_otp:
            generated_timestamp = request.session.get('otp_timestamp')

            # Validating email
            if email == request.session['email']:
                # Checking if OTP is expired
                if generated_timestamp:
                    generated_timestamp = datetime.datetime.fromisoformat(generated_timestamp)
                    if (datetime.datetime.now() - generated_timestamp).seconds > 300:
                        print("OTP expired...")
                        del request.session['generated_otp']
                        messages.error(request, "Your OTP has expired. Please click Resend OTP to get new one.")
                
                if user_entered_otp == request.session.get('generated_otp'):
                    print("OTP matching...")
                    user = User.objects.filter(username=email).first()
                    if user:
                        user.is_verified = True
                        user.save()
                        authlogin(request, user)
                        return redirect('index')
                else:
                    context.update({'stage': 'otp', 'email': email})
                    messages.error(request, "Entered OTP is invalid or expired!")
                return render(request, 'web/register.html', context=context)
            else:
                messages.error(request, "Something went wrong! Please try again.")
                del request.session['email']
                return redirect('login')
            
    return render(request, 'web/login.html', context=context)


def logout(request):
    authlogout(request)
    return redirect('index')


@user_passes_test(lambda user: not user.is_authenticated, login_url='/',redirect_field_name=None)
def recover(request):
    context = {
        'stage': "email"
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

            if user:
                if not user.is_blocked:
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
                            from_email="teamkepe@gmail.com",  # Your email address
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        messages.success(request, "A new OTP has been sent to your email.")
                    except:
                        messages.error(request, "Something went wrong while resending OTP. Please try again.")
                else:
                    messages.error(request, "Your account has been blocked by administrator. Please contact support@keynut.com for further assistance.")
            else:
                messages.error(request, "Entered email is not registered with us!")
                return redirect('admin_recover_password')
        
        # Validate OTP
        elif user_entered_otp and email:
            print("Validating OTP...")
            generated_timestamp = request.session.get('otp_timestamp')

            if generated_timestamp:
                generated_timestamp = datetime.datetime.fromisoformat(generated_timestamp)
                if (datetime.datetime.now() - generated_timestamp).seconds > 300:
                    print("OTP expired...")
                    del request.session['generated_otp']
                    messages.error(request, "Your OTP has expired. Please request a new one.")
            
            if user_entered_otp == request.session.get('generated_otp'):
                print("OTP matching...")
                request.session['otp_verified'] = True
                context.update({'stage': 'reset', 'email': email})
                messages.success(request, "OTP Verified! Please enter your new password.")
            else:
                context.update({'stage': 'otp', 'email': email})
                messages.error(request, "You entered an invalid OTP!")
        
        # Reset password
        elif password1 and password2 and email and request.session.get('otp_verified'):
            if password1 == password2:
                print("Reseting password...")
                user = User.objects.filter(username=email).first()
                if user:
                    user.set_password(password1)
                    user.save()
                    del request.session['otp_verified']
                    messages.success(request, "Password has been successfully updated. Please login with new password.")
                    return redirect('login')
                else:
                    messages.error(request, "User not found.")
            else:
                messages.error(request, "Passwords do not match.")
                context.update({'stage': 'reset', 'email': email})
        
        # Sendig OTP
        elif email:
            user = User.objects.filter(username=email).first()

            if user:
                if not user.is_blocked:
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
                            from_email="teamkepe@gmail.com",  # Your email address
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        messages.success(request, "OTP has been sent to your email.")
                    except:
                        messages.error(request, "Something went wrong while sending OTP. Please try again.")
                else:
                    messages.error(request, "Your account has been blocked by administrator. Please contact support@keynut.com for further assistance.")
            else:
                messages.error(request, "Entered email is not registered with us!")
    return render(request, 'web/recover.html', context=context)


@user_passes_test(lambda user: not user.is_authenticated, login_url='/',redirect_field_name=None)
def register(request):
    context = {
        'stage': "primary"
    }
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        resend_otp = request.POST.get('resend_otp')
        user_entered_otp = request.POST.get('otp')

        # Validating fields
        if first_name and last_name and email and phone and password1 and password2:
            if not User.objects.filter(username=email):
                if password1 == password2:

                    # Creating new user
                    user = User.objects.create_user(
                        username = email,
                        first_name = first_name,
                        last_name = last_name,
                        email = email,
                        phone = phone
                    )
                    user.set_password(password1)
                    user.save()

                    # Generate OTP
                    otp = str(random.randint(1000, 9999))
                    request.session['email'] = email
                    request.session['generated_otp'] = otp
                    request.session['otp_timestamp'] = str(datetime.datetime.now())
                    print(otp)

                    # Update context to next stage
                    context.update({
                        'stage': "otp",
                        'email': email
                    })
                    
                    # Send OTP to email
                    try:
                        send_mail(
                            subject="Your Keynut OTP Code",
                            message=f"Your OTP is {otp}. It expires in 5 minutes.",
                            from_email="teamkepe@gmail.com",  # Your email address
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        messages.success(request, "OTP has been sent to your email.")
                    except:
                        messages.error(request, "Something went wrong while sending OTP. Please click Resend OTP to send again.")
                else:
                    messages.error(request, "Passwords does not match!")
            else:
                messages.error(request, "This email is already registered with us! Please login.")
                return redirect('login')
        
        # Handling Resend OTP
        elif email and resend_otp:
            # Validating email
            if email == request.session['email']:
                # Generate OTP
                otp = str(random.randint(1000, 9999))
                request.session['generated_otp'] = otp
                request.session['otp_timestamp'] = str(datetime.datetime.now())
                print(otp)

                # Update context to next stage
                context.update({
                    'stage': "otp",
                    'email': email
                })
                
                # Send OTP to email
                try:
                    send_mail(
                        subject="Your Keynut OTP Code",
                        message=f"Your OTP is {otp}. It expires in 5 minutes.",
                        from_email="teamkepe@gmail.com",  # Your email address
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    messages.success(request, "OTP has been sent to your email.")
                except:
                    messages.error(request, "Something went wrong while sending OTP. Please click Resend OTP to send again.")
            else:
                messages.error(request, "Something went wrong! Please try again.")
                del request.session['email']
                return redirect('login')

        # Validating OTP
        elif email and user_entered_otp:
            generated_timestamp = request.session.get('otp_timestamp')

            # Validating email
            if email == request.session['email']:
                # Checking if OTP is expired
                if generated_timestamp:
                    generated_timestamp = datetime.datetime.fromisoformat(generated_timestamp)
                    if (datetime.datetime.now() - generated_timestamp).seconds > 300:
                        print("OTP expired...")
                        del request.session['generated_otp']
                        messages.error(request, "Your OTP has expired. Please click Resend OTP to get new one.")
                
                if user_entered_otp == request.session.get('generated_otp'):
                    print("OTP matching...")
                    user = User.objects.filter(username=email).first()
                    if user:
                        user.is_verified = True
                        user.save()
                        authlogin(request, user)
                        return redirect('index')
                else:
                    context.update({'stage': 'otp', 'email': email})
                    messages.error(request, "Entered OTP is invalid or expired!")
            else:
                messages.error(request, "Something went wrong! Please try again.")
                del request.session['email']
                return redirect('login')
        else:
            messages.error(request, "All fields are required!")
    return render(request, 'web/register.html', context=context)