import json

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib import messages
from django.db.models import F

from . forms import CustomerForm
from . models import Cart, CartItem
from products.models import Product, ProductVariant

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


    context.update({
        'cart': cart,
        'cart_items': cart_items,
    })
    return render(request, 'web/cart.html', context=context)


@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
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


@login_required(login_url='login')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def wishlist(request):
    pass