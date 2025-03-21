import random
import datetime
import tempfile

from django.shortcuts import render, redirect
from django.contrib.auth import login as authlogin, logout as authlogout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import F, Q, Exists, OuterRef, BooleanField, Case, When, Value
from django.core.mail import send_mail
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from weasyprint import HTML

from products.models import Product, Category
from customers.models import Address, Wishlist
from customers.forms import AddressForm
from orders.models import Order, OrderItem, Payment

User = get_user_model()


def index(request):
    context = {}
    categories = Category.objects.filter(is_deleted=False)
    
    flash_sales = Product.objects.filter(is_listed=True, is_deleted=False, category__is_deleted=False).order_by('-relevance')[:4]
    
    best_selling = Product.objects.filter(is_listed=True, is_deleted=False, category__is_deleted=False)[:4]
    
    new_arrivals = Product.objects.filter(is_listed=True, is_deleted=False, category__is_deleted=False).order_by('-created_at')[:4]

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
    

    products = Product.objects.filter(is_deleted=False, is_listed=True, category__is_deleted=False).order_by('-relevance')
    
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
    paginator = Paginator(products, 16)
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
    product = Product.objects.select_related('category').filter(slug=slug).first()
    if product and product.is_listed and not product.is_deleted and not product.category.is_deleted:
        product_variants = []
        for variant in product.variants.all().order_by('quantity'):
            formatted_quantity = variant.get_display_quantity(product.unit)  # Call the method
            product_variants.append({
                'id': variant.id,
                'quantity': variant.quantity,
                'formatted_quantity': formatted_quantity  # Store formatted quantity
            })
        context.update({
            'product': product,
            'product_variants': product_variants,
        })
    else:
        return redirect('404')

    # Check if in wishlist
    in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    # Getting related products to display
    related_products = Product.objects.select_related('category').filter(~Q(slug=slug)).order_by('-relevance')[:4]
    context.update({
        'related_products': related_products,
        'in_wishlist': in_wishlist,
    })
    return render(request, 'web/product_details.html', context=context)


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')

        # Update name
        if first_name and last_name:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()
            messages.success(request, "Profile updated successfully.")
        elif email:
            request.user.email = email
            request.user.username = email
            request.user.is_verified = False
            request.user.save()
            messages.success(request, "Email updated successfully.")
        elif phone:
            request.user.phone = phone
            request.user.save()
            messages.success(request, "Phone number updated successfully.")
        else:
            messages.error(request, "All fields are required!")
    return render(request, 'web/user_profile.html')


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current-password')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if current_password and password1 and password2:
            if password1 == password2:
                if request.user.check_password(password1):
                    request.user.set_password(password1)
                    request.user.save()
                    messages.success(request, "Password updated successfully.")
                else:
                    messages.error(request, "The current password you entered is incorrect.")
            else:
                messages.error(request, "New password and confirm password do not match.")
        else:
            messages.error(request, "All fields are required!")
    return render(request, 'web/user_change_password.html')


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_address(request):
    addresses = Address.objects.filter(user=request.user, is_deleted=False)
    form = AddressForm()
    context = {
        'addresses': addresses,
        'form': form
    }
    return render(request, 'web/user_address.html', context=context)


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            new_address = form.save(commit=False)
            new_address.user = request.user

            # Check if the user has any existing addresses
            if not Address.objects.filter(user=request.user).exists():
                new_address.is_default = True  # Set first address as default

            new_address.save()
            return JsonResponse({
                'success': True,
                'message': 'New address added successfully.'
            })
        else:
            JsonResponse({
                'error': True,
                'message': "Address details are invalid. Please verify details"
            })
    return JsonResponse({
        'error': True,
        'message': "Invalid request!"
    })


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_edit_address(request, pk):
    if request.method == 'POST':
        address = Address.objects.filter(pk=pk, user=request.user).first()
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)
            updated_address.user = request.user
            updated_address.save()
            return JsonResponse({
                'success': True,
                'message': "Address updated successfully."
            })
        else:
            return JsonResponse({
                'error': True,
                'message': "Address details are invalid. Please verify details."
            })
    
    # if request is GET, fetch existing details.
    address = Address.objects.filter(pk=pk, user=request.user).first()
    if address:
        return JsonResponse({
            'success': True,
            'name': address.name,
            'phone': address.phone,
            'address_line_1': address.address_line_1,
            'address_line_2': address.address_line_2,
            'landmark': address.landmark,
            'pin': address.pin,
            'city': address.city,
            'state': address.state,
        })
    else:
        return JsonResponse({
            'error': True,
            'message': "Address not found or access denied!"
        })


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_set_address_default(request, pk):
    selected_address = Address.objects.filter(pk=pk, user=request.user).first()
    if not selected_address:
        return redirect('404')
    
    # Remove default from current default address
    current_default_address = Address.objects.filter(user=request.user, is_default=True).first()
    current_default_address.is_default = False
    current_default_address.save()
    
    # Add default to selected address
    selected_address.is_default = True
    selected_address.save()
    return redirect('user_address')


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_delete_address(request, pk):
    if request.method == 'POST':
        address = Address.objects.filter(pk=pk, user=request.user).first()
        if address:
            address.delete()
            return JsonResponse({
                'success': True,
                'message': "Address deleted successfully."
            })
        else:
            return JsonResponse({
                'error': True,
                'message': "Address not found or access denied."
            })
    return JsonResponse({
                'success': True,
                'message': "Invalid request."
            })


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_orders(request):
    order_items = OrderItem.objects.filter(
        order__user=request.user).select_related('order').prefetch_related('order__payments').annotate(
        retry_payment=Case(
            # If order status is NOT "Pending", mark False (no need to retry payment)
            When(~Q(order__status="pending"), then=Value(False)),

            # If order is "Pending" AND has a "cash-on-delivery" payment, mark False
            When(
                Exists(
                    Payment.objects.filter(
                        order_id=OuterRef("order_id"),
                        payment_method="cash-on-delivery"
                    )
                ),
                then=Value(False),
            ),

            # If order is "Pending" AND has a "Success" payment with any method, mark False
            When(
                Exists(
                    Payment.objects.filter(
                        order_id=OuterRef("order_id"),
                        payment_status="success"
                    )
                ),
                then=Value(False),
            ),

            # Otherwise, mark True (Pending orders without successful payment or cash-on-delivery)
            default=Value(True),
            output_field=BooleanField()
        )
    ).order_by('-order__order_date')

    # Pagination
    paginator = Paginator(order_items, 10) # 10 Order items per page
    page_number = request.GET.get('page')
    order_items = paginator.get_page(page_number)

    context = {
        'order_items': order_items,
    }
    return render(request, 'web/user_orders.html', context=context)


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_view_order(request, order_id):
    order = Order.objects.prefetch_related('order_items').filter(order_id=order_id, user=request.user).first()

    payment = Payment.objects.filter(
        Q(order=order) & (Q(payment_status='success') | Q(payment_method='cash-on-delivery'))).first()

    if not order:
        return redirect('404')

    context = {
        'order': order,
        'payment': payment,
    }
    return render(request, 'web/user_order_details.html', context=context)


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_order_invoice(request, order_id):
    order = Order.objects.filter(order_id=order_id, user=request.user).first()

    if not order:
        return redirect('404')
    
    invoice_number = f"IN-{order.id:06d}-{order.order_date.strftime("%y%m%d")}"
    
    # return render(request, 'web/order_invoice.html', {'order': order, 'invoice_number': invoice_number})
    
    html_string = render_to_string("web/order_invoice.html", {"order": order, 'invoice_number': invoice_number})

    # Generate PDF
    html = HTML(string=html_string)
    pdf_file = tempfile.NamedTemporaryFile(delete=True)
    html.write_pdf(target=pdf_file.name)

    # Serve the file as response
    with open(pdf_file.name, "rb") as pdf:
        response = HttpResponse(pdf.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_id}.pdf"'
        return response


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_ratings(request):
    return render(request, 'web/user_ratings.html')


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
                        messages.success(request, "Your email verified successfully. Please login again.")
                        return redirect('login')
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
            generated_timestamp = request.session.get('otp_timestamp')
            if generated_timestamp:
                generated_timestamp = datetime.datetime.fromisoformat(generated_timestamp)
                if (datetime.datetime.now() - generated_timestamp).seconds < 300:
                    messages.error(request, "Please wait while the OTP reaches your inbox. If not received within 5 minutes, click 'Resend OTP'.")
                    context.update({'stage': 'otp', 'email': email})
                else:
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
                        context.update({'stage': 'email', 'email': email})
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
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        resend_otp = request.POST.get('resend_otp')
        user_entered_otp = request.POST.get('otp')

        # Validating fields
        if first_name and last_name and email and password1 and password2:
            if not User.objects.filter(username=email):
                if password1 == password2:

                    # Creating new user
                    user = User.objects.create_user(
                        username = email,
                        first_name = first_name,
                        last_name = last_name,
                        email = email
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
                    context.update({
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                    })
            else:
                messages.error(request, "This email is already registered with us! Please verify email.")
                context.update({
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                })
        
        # Handling Resend OTP
        elif email and resend_otp:
            # Validating expiry time
            generated_timestamp = request.session.get('otp_timestamp')
            if generated_timestamp:
                generated_timestamp = datetime.datetime.fromisoformat(generated_timestamp)
                if (datetime.datetime.now() - generated_timestamp).seconds < 300:
                    messages.error(request, "Please wait while the OTP reaches your inbox. If not received within 5 minutes, click 'Resend OTP'.")
                    context.update({'stage': 'otp', 'email': email})
                else:
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
            context.update({
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
            })
    return render(request, 'web/register.html', context=context)


class CustomGoogleLoginView(OAuth2LoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    def get(self, request, *args, **kwargs):
        # Immediately redirect to Google without rendering a confirmation page
        return self.get_login_redirect()


def four_not_four(request):
    return render(request, 'web/404.html')