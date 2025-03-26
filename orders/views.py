import json

from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib import messages
from django.db.models import Min
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse

import razorpay

from customers.models import Address, Cart, CartItem, Wallet, WalletTransaction
from products.models import Product
from promotions.services import OfferService
from . models import Order, OrderItem, OrderAddress, Payment, ReturnRequest
from . services import create_razorpay_order, verify_razorpay_signature


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
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
            return redirect('checkout')
        
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

        # Payment method
        payment_method = request.POST.get('payment-method')

        if not payment_method:
            messages.error(request, "Select a payment method before proceeding with checkout!")
            return redirect('checkout')
        
        # Getting cart total, shipping charge and cart level discount
        # moved to here to compare with wallet balance before proceeding with order
        cart_total,_,_ = cart.total_price()
        shipping_charge = cart.shipping_charge()
        _,_,cart_level_discount = cart.total_price()

        # Checking wallet balance for wallet orders before proceeding with order
        if payment_method == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance < cart_total + shipping_charge:
                messages.error(request, "Insufficient balance in wallet. Please select a different payment method.")
                return redirect('checkout')
        
        # Starting the order creation
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
                delivery_address = order_address,
                shipping_charge = shipping_charge,
                order_level_discount=cart_level_discount
            )

            # Apply OfferService for each cart item and create order items
            order_items = []
            for item in cart_items:
                product = item.product
                variant_quantity = item.variant.quantity
                quantity = item.quantity

                # Apply Offers and Coupons
                offer_service = OfferService(product, variant_quantity, quantity, user=request.user)
                offer_service.apply_offers()
                offer_service.apply_coupons()

                # Calculate Final Price
                final_price, applied_discount = offer_service.calculate_final_price()

                # Getting per unit discount amount
                discount_amount_per_unit = product.price - final_price
                print(f"Discount amount per unit: {discount_amount_per_unit}")
                print(f"Applied discount: {applied_discount}")
                
                # Create order item
                order_item = OrderItem(
                    order=order,
                    product=product,
                    variant=variant_quantity,
                    price=final_price,
                    quantity=quantity,
                    discount_amount=discount_amount_per_unit
                )
                order_items.append(order_item)

            OrderItem.objects.bulk_create(order_items)

            # Updating stock
            products_to_update = []

            for item in order_items:
                item.product.stock -= item.variant * item.quantity
                products_to_update.append(item.product)

            Product.objects.bulk_update(products_to_update, ["stock"])

            # Clear cart
            cart_items.delete()
            cart.coupon = None
            cart.save(update_fields=["coupon"])

            # Creating payment data
            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount,
                payment_method=payment_method
            )
        
            # Handle cash on delivery order
            if payment_method == 'cash-on-delivery':
                return render(request, 'web/order_placed.html')
            
            # Handle wallet payment order
            if payment_method == 'wallet':
                wallet.balance -= order.total_amount
                wallet.save(update_fields=["balance"])

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='payment',
                    amount=order.total_amount,
                    status='success',
                    notes=f"Payment for order {order.order_id}"
                )

                payment.transaction_id = 'WALLET'
                payment.payment_status = 'success'
                payment.save()

                order.status = 'confirmed'
                order.save()

                return render(request, 'web/order_placed.html')
                
            # Handling online payments
            if payment_method == 'razorpay':
                # Creating razor pay order
                razorpay_order = create_razorpay_order(order.total_amount)
                
                if razorpay_order['id']:
                    payment.payment_provider_order_id = razorpay_order['id']
                    payment.save()

                    context = {
                        "callback_url": "http://" + "127.0.0.1:8000" + "/razorpay/callback/",
                        "razorpay_key": settings.RAZORPAY_API_KEY,
                        "order": order,
                        'provider_id': razorpay_order['id']
                    }
                    return render(request, 'web/razorpay_payment.html', context=context)
                else:
                    return render(request, 'web/order_failed.html', {'order': order})
        

    # Handling GET request
    saved_addresses = Address.objects.filter(user=request.user)
    cart = Cart.objects.filter(user=request.user).first()
    
    context.update({
        'saved_addresses': saved_addresses,
        'cart': cart,
    })
    if cart.total_price()[0] > 0:
        return render(request, 'web/checkout.html', context=context)
    else:
        return redirect('cart')


@csrf_exempt
def razorpay_callback(request):
    if request.method == 'GET':
        return redirect('404')
    
    if "razorpay_signature" in request.POST:
        payment_id = request.POST.get("razorpay_payment_id", "")
        razorpay_order_id = request.POST.get("razorpay_order_id", "")
        signature_id = request.POST.get("razorpay_signature", "")

        payment_instance = Payment.objects.filter(payment_provider_order_id=razorpay_order_id).first()
        payment_instance.transaction_id = payment_id
        payment_instance.save()

        if verify_razorpay_signature(request.POST):
            payment_instance.payment_status = 'success'
            payment_instance.save()

            # Update order status to 'Confirmed'
            payment_instance.order.status = 'confirmed'
            payment_instance.order.save()

            return render(request, 'web/order_placed.html')
        else:
            payment_instance.payment_status = 'failed'
            payment_instance.save()
            return render(request, 'web/order_failed.html', {'order': payment_instance.order})
    
    else:
        payment_id = json.loads(request.POST.get("error[metadata]")).get("payment_id")
        razorpay_order_id = json.loads(request.POST.get("error[metadata]")).get(
            "order_id"
        )
        payment_instance = Payment.objects.filter(payment_provider_order_id=razorpay_order_id).first()
        payment_instance.transaction_id = payment_id
        payment_instance.payment_status = 'failed'
        payment_instance.save()
        return render(request, 'web/order_failed.html', {'order': payment_instance.order})


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def checkout_retry(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = Order.objects.filter(order_id=order_id, user=request.user).first()

        razorpay_order = create_razorpay_order(order.total_amount)
        if razorpay_order['id']:
            Payment.objects.create(
                order=order,
                amount=order.total_amount,
                payment_method='razorpay',
                payment_provider_order_id=razorpay_order['id']
            )
            context = {
                "callback_url": "http://" + "127.0.0.1:8000" + "/razorpay/callback/",
                "razorpay_key": settings.RAZORPAY_API_KEY,
                "order": order,
                'provider_id': razorpay_order['id']
            }
            return render(request, 'web/razorpay_payment.html', context=context)
        else:
            return render(request, 'web/order_failed.html', {'order': order})

    return redirect('404')


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
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


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def user_cancel_order(request):
    if request.method == 'POST':
        order_id = request.POST.get('order-id')
        cancellation_note = request.POST.get('cancellation-note')

        order = Order.objects.filter(order_id=order_id, user=request.user).first()
        if not order:
            return redirect('404')
        
        with transaction.atomic():
            order.status = "cancelled"
            order.notes += f"\nUser cancellation note: {cancellation_note}"
            order.save()

            # Refunding amount to wallet
            payment = order.payments.filter(payment_status='success').first()
            if payment:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += order.total_amount + order.shipping_charge
                wallet.save(update_fields=["balance"])

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    amount=order.total_amount + order.shipping_charge,
                    status='success',
                    notes=f"Refund for order {order.order_id}"
                )

                messages.success(request, f"Order {order.order_id} has been cancelled successfully. The amount has been refunded to your wallet.")
            else:
                messages.success(request, f"Order {order.order_id} has been cancelled successfully.")

            # Updating stock
            products_to_update = []

            for item in order.order_items.all():
                item.product.stock += item.variant * item.quantity
                products_to_update.append(item.product)

            Product.objects.bulk_update(products_to_update, ["stock"])
        
        return redirect('user_view_order', order_id=order.order_id)
    
    return redirect('404')


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def user_return_order(request):
    if request.method == 'POST':
        order_id = request.POST.get('order-id')
        return_reason = request.POST.get('return-reason')

        order = Order.objects.filter(order_id=order_id, user=request.user).first()
        if not order:
            return redirect('404')
        
        ReturnRequest.objects.create(
            order=order,
            reason=return_reason
        )
        order.status = 'return_requested'
        order.save()

        messages.success(request, f"We have received your return request for order {order.order_id}. Once the request is approved, you will receive an email with instructions on how to return.")
                
        return redirect(reverse('user_view_order', kwargs={'order_id':order.order_id}))
    
    return redirect('404')


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def process_return_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get("request_id")
            new_status = data.get("status")

            if not new_status:
                return JsonResponse({
                    'error': True,
                    'message': "Nothing to update!"
                })

            return_request = ReturnRequest.objects.filter(id=request_id).first()
            if return_request:
                return_request.status = new_status
                return_request.save(update_fields=["status"])

                # Update order status
                if new_status == 'approved':
                    return_request.order.status = 'return_approved'
                    return_request.order.save(update_fields=["status"])
                
                elif new_status == 'rejected':
                    return_request.order.status = 'return_rejected'
                    return_request.order.save(update_fields=["status"])

                return JsonResponse({
                    'success': True,
                    'message': "Return status updated successfully."
                })
            else:
                return JsonResponse({
                    'error': True,
                    'message': "Return request not found!"
                })
        
        except Exception as e:
            return JsonResponse({'error': True, "message": str(e)})

    return JsonResponse({'error': True, "message": "Invalid request"})
