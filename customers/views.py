import json

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib import messages
from django.db.models import F, Q
from django.utils.timezone import now

from . forms import CustomerForm
from . models import Wishlist, Cart, CartItem, Subscriber
from products.models import Product, ProductVariant, Category
from promotions.services import OfferService
from promotions.models import Coupon

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
        user = User.objects.filter(pk=pk).first()
        if user:
            print("getting user..")
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


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def wishlist(request):
    whishlist_items = Wishlist.objects.filter(user=request.user)

    suggested_products = products = Product.objects.filter(is_deleted=False, is_listed=True, category__is_deleted=False).order_by('-relevance')[:4]
    context = {
        'wishlist_items': whishlist_items,
        'suggested_products': suggested_products,
    }
    return render(request, 'web/wishlist.html', context=context)


def toggle_wishlist(request, product_id):
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


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def cart(request):
    context = {}
    cart = Cart.objects.filter(user=request.user).first()
    cart_items = CartItem.objects.filter(cart__user=request.user)
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
    for item in cart_items:
        if item.quantity * item.variant.quantity > item.product.stock:
            item.quantity = int(item.product.stock / item.variant.quantity)

    products_in_carts = Product.objects.filter(cartitem__cart__user=request.user)
    categories_in_carts = Category.objects.filter(product__cartitem__cart__user=request.user)
    available_coupons = Coupon.objects.filter((
        ((Q(products=None) & Q(categories=None)) & (Q(users=None) | Q(users=request.user))) | 
        (Q(products__in=products_in_carts) & (Q(users=None) | Q(users=request.user))) | 
        (Q(categories__in=categories_in_carts) & (Q(users=None) | Q(users=request.user)))
    ) & (Q(start_date__lte=now()) & Q(end_date__gte=now())))

    context.update({
        'cart': cart,
        'cart_items': cart_items,
        'available_coupons': available_coupons,
    })
    return render(request, 'web/cart.html', context=context)


def add_to_cart(request):
    # Handling not logged in user - redirect to product page after login
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
                # Get or create cart
                user_cart, created = Cart.objects.get_or_create(user=request.user)

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
    # Handling not logged in user - redirect to product page after login
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
                user_cart, created = Cart.objects.get_or_create(user=request.user)

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
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon-code','').upper()
        # if not coupon_code:
        #     return redirect('cart')

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
    return redirect('cart')


def offer_subscibe(request):
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
