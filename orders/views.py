import json
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib import messages
from django.db.models import Min
from django.http import JsonResponse

from customers.models import Address, Cart, CartItem
from products.models import Product
from . models import Order, OrderItem, OrderAddress


def checkout(request):
    context = {}
    if request.method == 'POST':

        # Checking cart items
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return redirect('cart')
        
        cart_items = CartItem.objects.filter(cart=cart)
        if not cart_items:
            return redirect('cart')
        
        # Checking out of stock issues
        stock_error = False
        minimum_stock_available = True
        for item in cart_items:
            if item.variant.quantity * item.quantity > item.product.stock:
                stock_error = True
            if stock_error:
                smallest_variant = item.product.variants.all().aggregate(Min('quantity'))['quantity__min']
                if smallest_variant > item.product.stock:
                    minimum_stock_available = False
        
        if stock_error:
            if minimum_stock_available:
                messages.error(request, f"Oops! Looks like some items just got snapped up by other shoppers. We currently have only {item.product.stock} {item.product.unit} of {item.product.name} left in stock. Please update your variant and quantity to proceed. Thanks for understanding!")
            
            if not minimum_stock_available:
                messages.error(request, f"Oops! Looks like some items just got snapped up by other shoppers. Please remove 'Out of Stock' items from your cart to proceed. Thanks for understanding!")
            
            return redirect('cart')
            

        # Getting delivery address
        address_id = request.POST.get('delivery-address')

        if not address_id:
            messages.error(request, "Add a delivery address before proceeding with checkout!")
            return redirect('cart')
        
        if address_id == 'new-address':
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            address_line_1 = request.POST.get('address_line_1')
            address_line_2 = request.POST.get('address_line_2', '')
            landmark = request.POST.get('landmark', '')
            pin = request.POST.get('pin')
            city = request.POST.get('city')
            state = request.POST.get('state')
            save_address = request.POST.get('save_address') == 'yes'

            if save_address:
                selected_address = Address.objects.filter(
                    user = request.user,
                    name = name,
                    phone = phone,
                    address_line_1 = address_line_1,
                    address_line_2 = address_line_2,
                    landmark = landmark,
                    pin = pin,
                    city = city,
                    state = state
                ).first()

                # If no matching address found, create a new one
                if not selected_address:
                    selected_address = Address.objects.create(
                        user=request.user,
                        name=name,
                        phone=phone,
                        address_line_1=address_line_1,
                        address_line_2=address_line_2,
                        landmark=landmark,
                        pin=pin,
                        city=city,
                        state=state
                    )
            
            # If not saving address, get a temporary address object
            else:
                selected_address = Address(
                    user=request.user,
                    name=name,
                    phone=phone,
                    address_line_1=address_line_1,
                    address_line_2=address_line_2,
                    landmark=landmark,
                    pin=pin,
                    city=city,
                    state=state
                )
        
        # if existing address is selected
        else:
            selected_address = Address.objects.filter(pk=address_id).first()
    
        with transaction.atomic(): # Ensures atomicity
            
            # Create order address
            order_address = OrderAddress.objects.filter(
                user = request.user,
                name = selected_address.name,
                phone = selected_address.phone,
                address_line_1 = selected_address.address_line_1,
                address_line_2 = selected_address.address_line_2,
                landmark = selected_address.landmark,
                pin = selected_address.pin,
                city = selected_address.city,
                state = selected_address.state
            ).first()

            if not order_address:  # If no exact match found, create a new one
                order_address = OrderAddress.objects.create(
                    user=request.user,
                    name=selected_address.name,
                    phone=selected_address.phone,
                    address_line_1=selected_address.address_line_1,
                    address_line_2=selected_address.address_line_2,
                    landmark=selected_address.landmark,
                    pin=selected_address.pin,
                    city=selected_address.city,
                    state=selected_address.state
                )

            # Creating order instance
            order = Order.objects.create(
                user = request.user,
                delivery_address = order_address
            )

            # Creating order items in bulk
            order_items = [
                OrderItem(
                    order = order,
                    product = item.product,
                    variant = item.variant.quantity,
                    price = item.product.price,
                    quantity = item.quantity
                )
                for item in cart_items
            ]

            OrderItem.objects.bulk_create(order_items)

            # Updating stock
            products_to_update = []

            for item in order_items:
                item.product.stock -= item.variant * item.quantity
                products_to_update.append(item.product)

            Product.objects.bulk_update(products_to_update, ["stock"])

            # Clear cart
            cart_items.delete()

        return render(request, 'web/order_placed.html')

    # Handling GET request
    saved_addresses = Address.objects.filter(user=request.user)
    cart = Cart.objects.filter(user=request.user).first()
    
    context.update({
        'saved_addresses': saved_addresses,
        'cart': cart,
    })
    if cart.total_price() > 0:
        return render(request, 'web/checkout.html', context=context)
    else:
        return redirect('cart')


def update_order_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get("order_id")
            new_status = data.get("status")

            if not new_status:
                return JsonResponse({
                    'error': True,
                    'message': "Nothing to update!"
                })

            order = Order.objects.filter(id=order_id).first()
            if order:
                order.status = new_status
                order.save(update_fields=["status"])

                return JsonResponse({
                    'success': True,
                    'message': "Order status updated successfully."
                })
            else:
                return JsonResponse({
                    'error': True,
                    'message': "Order not found!"
                })
        
        except Exception as e:
            return JsonResponse({'error': True, "message": str(e)})

    return JsonResponse({'error': True, "message": "Invalid request"})