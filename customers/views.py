import json

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib import messages
from django.db.models import F, Q

from . forms import CustomerForm
from . models import Wishlist, Cart, CartItem, Subscriber
from products.models import Product, ProductVariant, Category
from promotions.services import OfferService
from promotions.models import Coupon

User = get_user_model()


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def add_customer(request):
    """Add new customer from admin panel."""
    if request.POST:
        form = CustomerForm(request.POST)
        if form.is_valid:
            user = form.save(commit=False)
            user.username = request.POST['email']
            user.set_password(request.POST['password'])
            user.save()
            return JsonResponse({
                "success": True,
                "message": f"Customer {request.POST['first_name']} added successfully."
            })
        else:
            return JsonResponse({
                "error": True,
                "message": "Form validation error! Please verify all details."
            })
    else:
        return JsonResponse({
            "error": True,
            "message": "Invalid request!"
        })
    

@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def edit_customer(request, pk=None):
    """Edit customer from admin panel
    
    GET request: fetch customer data
    POST request: update customer data
    """
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        user = User.objects.filter(pk=pk).first()
        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
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
    
    # if GET request, fetch customer data
    else:
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
    """Customer blocking and unblocking from admin panel."""
    if request.method == "POST":
        try:
            user = get_object_or_404(User, pk=pk)
            user.is_blocked = not user.is_blocked
            user.save()
            
            # Send notification email to customer
            try:
                send_mail(
                    subject=f"Your Keynut account has been {'blocked' if user.is_blocked else 'unblocked'}.",
                    message=f"Your Keynut account has been {'blocked' if user.is_blocked else 'unblocked'} by administrator{' in regarding to the violation of terms and conditions. Please contact support@keynut.com for further assistance.' if user.is_blocked else '.'}",
                    from_email="teamkepe@gmail.com",  # Your email address
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except:
                return JsonResponse({
                    "success" : True,
                    "message" : f"Customer {user.first_name} has {'blocked' if user.is_blocked else 'unblocked'} successfully. But, notification email was not sent to the customer due some technical issues."
                })

            return JsonResponse({
                "success" : True,
                "message" : f"Customer {user.first_name} has {'blocked' if user.is_blocked else 'unblocked'} successfully."
            })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)


def toggle_wishlist(request, product_id):
    """Add or remove product to/from Wishlist."""
    # Handle not logged in users
    if not request.user.is_authenticated:
        return JsonResponse({'error': True, 'message': 'Please log in to manage your wishlist.'}, status=401)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': True, 'message': 'Product not found.'}, status=404)

    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if not created:
        wishlist_item.delete()
        return JsonResponse({'success': True, 'message': 'Removed from wishlist', 'in_wishlist': False})
    else:
        return JsonResponse({'success': True, 'message': 'Added to wishlist', 'in_wishlist': True})


def add_to_cart(request):
    """Add to cart from product details page."""
    # Handling not logged in user - redirect to product details page after login
    if not request.user.is_authenticated:
        product = Product.objects.filter(
            id=request.POST.get('product_id'),
            is_listed=True,
            is_deleted=False,
            category__is_deleted=False
        ).first()

        redirect_url = f"{reverse('login')}?next={reverse('product_details', kwargs={'slug': product.slug})}"
        return redirect(redirect_url)
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        variant_id = request.POST.get('selected_variant')
        quantity = int(request.POST.get('quantity'))

        product = Product.objects.filter(id=product_id, is_listed=True, is_deleted=False, category__is_deleted=False).first()
        variant = ProductVariant.objects.filter(id=variant_id).first()

        if quantity  > 10:
            quantity = 10
            messages.error(request, "Maximum quantity of a product in single order is capped at 10.")
        
        if product and variant:
            if variant.quantity * quantity <= product.stock:
                # Get existing cart or create cart if no existing found
                user_cart, _ = Cart.objects.get_or_create(user=request.user)

                # Get or create the product with the given variant
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=product,
                    variant=variant,
                    defaults={"quantity": quantity}  # Set quantity if creating new
                )

                # If item already exists, update quantity
                if not created:
                    cart_item.quantity = F("quantity") + quantity
                    cart_item.save(update_fields=["quantity"])
                
                # Ensure the quantity does not exceed 10 - this case is needed if product already exists in cart
                cart_item.refresh_from_db()  # Fetch the updated value from DB
                if cart_item.quantity > 10:
                    cart_item.quantity = 10
                    cart_item.save(update_fields=["quantity"])
                
                messages.success(request, f"{product.name} - {variant.quantity} {product.unit} added to cart successfully.")
            else:
                messages.error(request, f"Oops! Looks like some items just got snapped up by other shoppers. We currently have only {product.stock} {product.unit} left in stock. Please update your variant and quantity to proceed. Thanks for understanding!")
                return redirect(reverse('product_details', kwargs={'slug': product.slug}))
        else:
            return redirect('404')
    else:
        messages.error(request, "We got an invalid request! Please confirm and try again.")
    return redirect('cart')


def add_to_cart_card(request, pk):
    """Add to cart from product card."""
    # Handling not logged in user
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': True,
            'message': 'Please login to add products to cart.'
        })
    
    if request.method == 'POST':
        product = Product.objects.filter(pk=pk, is_listed=True, is_deleted=False, category__is_deleted=False).first()
        
        variant = product.variants.filter(quantity=1).first() or product.variants.all().order_by('quantity').first()
        
        if product and variant:
            if variant.quantity <= product.stock:
                # Get or create cart
                user_cart, _ = Cart.objects.get_or_create(user=request.user)

                # Get or create the product with the given variant
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=product,
                    variant=variant,
                    defaults={"quantity": 1}  # Set quantity if creating new
                )

                # If item already exists, update quantity
                if not created:
                    cart_item.quantity = F("quantity") + 1
                    cart_item.save(update_fields=["quantity"])
                
                # Ensure the quantity does not exceed 10 - this case is needed if product already exists in cart
                cart_item.refresh_from_db()  # Fetch the updated value from DB
                if cart_item.quantity > 10:
                    cart_item.quantity = 10
                    cart_item.save(update_fields=["quantity"])
                
                return JsonResponse({
                    'success': True,
                    'message': f"{product.name} - {variant.quantity} {product.unit} added to cart successfully."
                })
            else:
                return JsonResponse({
                    'error': True,
                    'message': f"Oops! Looks like some items just got snapped up by other shoppers. We currently have only {product.stock} {product.unit} left in stock. Please update your variant and quantity to proceed. Thanks for understanding!"
                })
        else:
            return JsonResponse({
                'error': True,
                'message': "Something went wrong. Please open product details and then add to cart."
            })
    else:
        return JsonResponse({
            'error': True,
            'message': "Invalid request!"
        })


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def remove_from_cart(request, pk):
    """Remove product from cart."""
    if request.method == 'POST':
        order_item = CartItem.objects.filter(pk=pk)
        
        if not order_item:
            return JsonResponse({
                'error': True,
                'message': "Item not found!"
            })
        
        order_item.delete()
        messages.success(request, "Item removed from cart successfully.")
        
        return JsonResponse({
            'success': True,
            'message': "Item removed from cart successfully."
        })


def apply_coupon(request):
    """Add coupon from cart. Validate coupon and apply to cart if valid."""
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon-code','').upper()

        coupon = Coupon.objects.filter(code=coupon_code).first()
        cart = Cart.objects.get(user=request.user)
        if coupon:
            try:
                # Initialize OfferService and validate coupon
                offer_service = OfferService(
                    product=None, 
                    variant_quantity=None, 
                    quantity=None, 
                    user=request.user, 
                    coupon_code=coupon.code
                )
                offer_service.validate_coupon(cart_total=cart.total_price()[0])

                # Store valid coupon in the cart
                cart.coupon = coupon
                cart.save()

                return redirect('cart')
        
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('cart')
            except Cart.DoesNotExist:
                messages.error(request, "Something went wrong! Please try again.")
        else:
            cart.coupon = None
            cart.save()
            messages.error(request, "Invalid coupon code!")
    return redirect('cart')


def offer_subscibe(request):
    """Newsletter subscription registration."""
    if not request.user.is_authenticated:
        return JsonResponse({
                    'error': True,
                    'message': 'Please login first.'
                })
    
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        
        if email == request.user.email:
            _, created = Subscriber.objects.get_or_create(email=email)
            if created:
                return JsonResponse({
                    'success': True,
                    'message': 'Subscribed successfully.'
                })
            else:
                return JsonResponse({
                    'error': True,
                    'message': 'Already subscribed!'
                })
        else:
            return JsonResponse({
                'error': True,
                'message': 'You cannot subscribe others!'
            })
    return JsonResponse({
        'error': True,
        'message': 'Invalid request!'
    })
