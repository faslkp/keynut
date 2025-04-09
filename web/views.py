import random
import datetime
import tempfile
import re
import uuid
import json

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
from django.utils import timezone

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from weasyprint import HTML

from products.models import Product, Category, Rating
from customers.models import Address, Wishlist, Cart, CartItem, Wallet, WalletTransaction, Message
from customers.forms import AddressForm
from orders.models import Order, OrderItem, Payment
from promotions.models import Offer, Coupon
from orders.views import cancel_old_pending_orders

User = get_user_model()


def index(request):
    """Home page rendering."""
    categories = Category.objects.filter(is_deleted=False)
    
    flash_sales = Product.objects.filter(is_listed=True, is_deleted=False, category__is_deleted=False).order_by('-relevance')[:4]
    
    best_selling = Product.objects.filter(is_listed=True, is_deleted=False, category__is_deleted=False)[:4]
    
    new_arrivals = Product.objects.filter(is_listed=True, is_deleted=False, category__is_deleted=False).order_by('-created_at')[:4]

    offers = Offer.objects.filter(is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now()).order_by('?')
    
    context = {
        'categories': categories, 
        'flash_sales': flash_sales,
        'best_selling': best_selling,
        'new_arrivals': new_arrivals,
        'top_banner_offer':offers[1] if offers and len(offers) >= 2 else None,
        'main_offer':offers[0] if offers else None,
        'second_offer': offers[2] if offers and len(offers) >= 3 else None
    }
    return render(request, 'web/index.html', context=context)


def products(request):
    """Products listing page rendering.
    
    Handle search, filter, sort queries.
    """
    q = request.GET.get('q')
    sortby = request.GET.get('sort')
    selected_categories = request.GET.getlist('category')
    selected_prices = request.GET.getlist('price')
    ref = request.GET.get('ref')
    
    if ref:
        current_time = timezone.now()

        active_offers = Offer.objects.filter(is_active=True, start_date__lte=current_time, end_date__gte=current_time)

        products = Product.objects.filter((Q(offers__in=active_offers) | Q(category__offers__in=active_offers)), is_deleted=False, is_listed=True, category__is_deleted=False)
    else:
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
                    price_query |= Q(price__gte=min_price)
                else:
                    price_query |= Q(price__gte=min_price, price__lte=max_price)
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
    context = {
        'products': products,
        'categories': categories
    }
    return render(request, 'web/products.html', context=context)


def product_details(request, slug):
    """Product details page rendering."""
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
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    # Getting related products to display
    related_products = Product.objects.select_related('category').filter(~Q(slug=slug)).order_by('-relevance')[:4]

    current_time = timezone.now()

    product_offers = product.offers.filter(is_active=True, start_date__lte=current_time, end_date__gte=current_time)
    category_offers = product.category.offers.filter(is_active=True, start_date__lte=current_time, end_date__gte=current_time)
    all_offers = product_offers | category_offers

    context.update({
        'related_products': related_products,
        'in_wishlist': in_wishlist,
        'offers': all_offers
    })
    return render(request, 'web/product_details.html', context=context)


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_profile(request):
    """User profile page.
    
    POST request update user profile.
    GET request render the profile page.
    """
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')

        if first_name and last_name:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()
            messages.success(request, "Profile updated successfully.")
        elif email:
            if User.objects.filter(email=email).exists():
                messages.error(request, "Entered email is already registered with us. Please use another email or login with the entered email.")
                return redirect('user_profile')
            request.user.email = email
            request.user.username = email
            request.user.is_verified = False
            request.user.save()
            messages.success(request, "Email updated successfully. Please login again with updated email.")
            authlogout(request)
            return redirect('login')
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
    """User side password changing."""
    if request.method == 'POST':
        current_password = request.POST.get('current-password')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if current_password and password1 and password2:
            if password1 == password2:
                if request.user.check_password(current_password):
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
    """User Addresses listing page."""
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
    """User add new address."""
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
    """User edit address.
    
    POST request update address.
    GET request fetch address details.
    """
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
    """User set default address."""
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
    """User delete address."""
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
    """User orders listing page."""
    # Cancel all pending orders before 3 days
    cancel_old_pending_orders()

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
    """Order details page rendering."""
    order = Order.objects.prefetch_related('order_items').filter(order_id=order_id, user=request.user).first()

    payment = Payment.objects.filter(
        Q(order=order) & (Q(payment_status='success') | Q(payment_method='cash-on-delivery'))).first()
    
    if not order:
        return redirect('404')

    # Get product IDs from order items for getting user's rating
    product_ids = order.order_items.values_list('product_id', flat=True)

    # Fetch user's ratings as a dictionary {product_id: rating}
    user_ratings = {r.product_id: r.rating for r in Rating.objects.filter(product_id__in=product_ids, user=request.user)}

    # Attach user rating to each order item
    for item in order.order_items.all():
        item.user_rating = user_ratings.get(item.product.id, None)

    total_amount = order.total_amount
    total_items_discount = order.total_discount
    total_discount = total_items_discount + order.order_level_discount
    shipping_charge = order.shipping_charge
    subtotal = total_amount + total_discount
    final_amount = total_amount + shipping_charge

    context = {
        'order': order,
        'payment': payment,
        'subtotal': subtotal,
        'shipping_charge': shipping_charge,
        'total_discount': total_discount,
        'final_amount': final_amount
    }
    return render(request, 'web/user_order_details.html', context=context)


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_order_invoice(request, order_id):
    """Generate order invoice pdf dynamically."""
    order = Order.objects.filter(order_id=order_id, user=request.user).first()

    if not order:
        return redirect('404')
    
    invoice_number = f"IN-{order.id:06d}-{order.order_date.strftime('%y%m%d')}"

    total_amount = order.total_amount
    total_items_discount = order.total_discount
    total_discount = total_items_discount + order.order_level_discount
    shipping_charge = order.shipping_charge
    subtotal = total_amount + total_discount
    final_amount = total_amount + shipping_charge

    context = {
        "order": order,
        'invoice_number': invoice_number,
        'subtotal': subtotal,
        'shipping_charge': shipping_charge,
        'total_discount': total_discount,
        'final_amount': final_amount
    }
    
    html_string = render_to_string("web/order_invoice.html", context=context)

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
    """User ratings page."""
    ratings = Rating.objects.select_related('product').filter(user=request.user)

    paginator = Paginator(ratings, 10)
    page_number = request.GET.get('page')
    ratings = paginator.get_page(page_number)

    context = {
        'ratings': ratings
    }
    return render(request, 'web/user_ratings.html', context=context)


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def add_rating(request):
    """Add product rating by user."""
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        rating = int(data.get('rating'))

        if rating < 1 or rating > 5:
            return JsonResponse({
                'error': True,
                'message': "Invalid rating!"
            })

        product = Product.objects.filter(id=product_id).first()
        
        if not product:
            return JsonResponse({
                'error': True,
                'message': "Product not found!"
            })
        
        new_rating, _ = Rating.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'rating': rating}
        )

        return JsonResponse({
            'success': True,
            'message': "Rating added."
        })

    return JsonResponse({
        'error': True,
        'message': "Invalid request!"
    })


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def wallet(request):
    """Wallet and wallet transactions page."""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by('-created_at')

    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)

    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'web/user_wallet.html', context=context)


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def wishlist(request):
    """Wishlist rendering."""
    whishlist_items = Wishlist.objects.filter(user=request.user)

    suggested_products = products = Product.objects.filter(is_deleted=False, is_listed=True, category__is_deleted=False).order_by('-relevance')[:4]
    context = {
        'wishlist_items': whishlist_items,
        'suggested_products': suggested_products,
    }
    return render(request, 'web/wishlist.html', context=context)


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def cart(request):
    """Cart page rendering."""
    context = {}
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    if request.method == 'POST':
        quantity_above_10 = False
        for item in cart_items:
            new_quantity = int(request.POST.get(str(item.id), 1))  # Get updated quantity
            item.quantity = min(new_quantity, 10)  # Ensure max 10
            item.save(update_fields=["quantity"])
            if new_quantity > 10:
                quantity_above_10 = True
        if quantity_above_10:
            messages.error(request, "Maximum quantity of a product in single order is capped at 10.")
    
    # Handle quantity based on stock
    if cart_items:
        for item in cart_items:
            if item.quantity * item.variant.quantity > item.product.stock:
                item.quantity = int(item.product.stock / item.variant.quantity)

        products_in_carts = Product.objects.filter(cartitem__cart=cart)
        categories_in_carts = Category.objects.filter(product__cartitem__cart=cart)
        available_coupons = Coupon.objects.filter((
            ((Q(products=None) & Q(categories=None)) & (Q(users=None) | Q(users=request.user))) | 
            (Q(products__in=products_in_carts) & (Q(users=None) | Q(users=request.user))) | 
            (Q(categories__in=categories_in_carts) & (Q(users=None) | Q(users=request.user)))
        ) & (Q(start_date__lte=timezone.now()) & Q(end_date__gte=timezone.now())))
    
        total_amount, total_discount, _ = cart.total_price()
        shipping_charge = cart.shipping_charge()
        subtotal = total_amount + total_discount
        final_amount = total_amount + shipping_charge
        
        context.update({
            'available_coupons': available_coupons,
            'subtotal': subtotal,
            'shipping_charge': shipping_charge,
            'total_discount': total_discount,
            'final_amount': final_amount
        })

    context.update({
        'cart': cart,
        'cart_items': cart_items
    })
    return render(request, 'web/cart.html', context=context)


@never_cache
@user_passes_test(lambda user: not user.is_authenticated, login_url='/',redirect_field_name=None)
def login(request):
    """User login."""
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
    """User logout."""
    authlogout(request)
    return redirect('index')


@user_passes_test(lambda user: not user.is_authenticated, login_url='/',redirect_field_name=None)
def recover(request):
    """User recover password - Forgot password."""
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
    """User registration."""
    referral_key = request.GET.get('ref', '')
    context = {
        'stage': "primary",
        'referral_key': referral_key
    }
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        resend_otp = request.POST.get('resend_otp')
        user_entered_otp = request.POST.get('otp')
        referral_key = request.POST.get('referral_key')

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

                    # Handling referral key
                    if referral_key:
                        user.referral_key = f"ref-{referral_key}-{user.username}"
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
                messages.error(request, "This email is already registered with us! Please check entered email or login with credentials.")
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
                        del request.session['generated_otp']
                        messages.error(request, "Your OTP has expired. Please click Resend OTP to get new one.")
                
                if user_entered_otp == request.session.get('generated_otp'):
                    user = User.objects.filter(username=email).first()
                    if user:
                        # Handling referral
                        if user.referral_key:
                            referred_by = None

                            re_pattern = rf"^ref-(.*)-{re.escape(user.username)}$"  # Pattern to match referral key
                            match = re.match(re_pattern, user.referral_key)
                            if match:
                                referral_key = match.group(1)
                                referred_by = User.objects.filter(referral_key=referral_key).first()

                                if referred_by:
                                    referrer_wallet, _ = Wallet.objects.get_or_create(user=referred_by)
                                    referrer_wallet.balance += 100
                                    referrer_wallet.save()
                                    WalletTransaction.objects.create(
                                        wallet=referrer_wallet,
                                        transaction_type='referral',
                                        transaction_id=uuid.uuid4(),
                                        amount=100,
                                        status='success',
                                        notes=f"Received on referring {user.first_name}"
                                    )

                                    user_wallet, _ = Wallet.objects.get_or_create(user=user)
                                    user_wallet.balance += 50
                                    user_wallet.save()
                                    WalletTransaction.objects.create(
                                        wallet=user_wallet,
                                        transaction_type='referral',
                                        transaction_id=uuid.uuid4(),
                                        amount=50,
                                        status='success',
                                        notes=f"Referred by {referred_by.first_name}"
                                    )

                                    messages.success(request, "You have been referred by a friend. You both have received Keynut bonus in your wallet.")
                                else:
                                    messages.error(request, "Invalid referral key!")

                        user.is_verified = True
                        user.save()

                        user.backend = 'django.contrib.auth.backends.ModelBackend'
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
    """404 error or access restricted error showing page."""
    return render(request, 'web/404.html')


def about(request):
    """About Us page."""
    return render(request, 'web/about.html')


def contact(request):
    """Conatact Us page with contact form."""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')

        if not name or not email or not phone or not message:
            messages.error(request, "All fields are required.")
            return redirect('contact')
        
        new_enquiry = Message.objects.create(
            user = request.user if request.user.is_authenticated else None,
            name = name,
            email = email,
            phone = phone,
            message = message
        )
        messages.success(request, f"We have received your message with acknowledge number {new_enquiry.acknowledge_number}. Please note it down so you can refer in future communications.")

    return render(request, 'web/contact.html')