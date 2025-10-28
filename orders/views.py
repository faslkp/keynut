import json
import uuid
import datetime

from decimal import Decimal

from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib import messages
from django.db.models import Min
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.utils import timezone

from customers.models import Address, Cart, CartItem, Wallet, WalletTransaction
from products.models import Product
from promotions.services import OfferService
from . models import Order, OrderItem, OrderAddress, Payment, ReturnRequest
from . services import create_razorpay_order, verify_razorpay_signature


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def checkout(request):
    """Create Order, Order Item, and Payment instances.
    
    For Cash on Delivery and Wallet orders, order is completly placed from here.
    For RazorPay, after creating pending payment instance, redirected to RazorPay.
    """
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
            save_address = request.POST.get('save-address') == 'yes'

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
                        state=state,
                        is_default=not Address.objects.filter(user=request.user).exists()
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
        
        # Checking cash on delivery and wallet payment eligibility
        # Getting cart total, shipping charge and cart level discount
        cart_total,_,cart_level_discount = cart.total_price()
        shipping_charge = cart.shipping_charge()

        # Checking cash on delivery eligibility
        if payment_method == 'cash-on-delivery' and (cart_total + shipping_charge) >= 1000:
            messages.error(request, "Orders with total amount above ₹1000 is not eligible for Cash on Delivery.")
            return redirect('checkout')

        # Checking wallet balance for wallet orders before proceeding with order
        if payment_method == 'wallet':
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance < cart_total + shipping_charge:
                messages.error(request, "Insufficient balance in wallet. Please select a different payment method.")
                return redirect('checkout')
        
        # Starting the order creation
        with transaction.atomic(): # Ensures atomicity
            
            # Create order address; first, checking if the same address is already existing
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
                order_level_discount=cart_level_discount,
                coupon=cart.coupon
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
                
                # Create order item
                order_item = OrderItem(
                    order=order,
                    product=product,
                    variant=variant_quantity,
                    price=final_price / (variant_quantity * Decimal(quantity)),
                    quantity=quantity,
                    discount_amount=applied_discount
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
            order_total_amount = order.total_amount + order.shipping_charge

            payment = Payment.objects.create(
                order=order,
                user=request.user,
                payment_type='payment',
                amount=order_total_amount,
                payment_method=payment_method
            )
        
            # Handle cash on delivery order
            if payment_method == 'cash-on-delivery':
                return render(request, 'web/order_placed.html', {'order': order})
            
            # Handle wallet payment order
            if payment_method == 'wallet':
                wallet.balance -= order_total_amount
                wallet.save(update_fields=["balance"])

                wallet_transaction = WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='payment',
                    transaction_id=uuid.uuid4(),
                    amount=order_total_amount,
                    status='success',
                    notes=f"Payment for order {order.order_id}",
                    order=order
                )

                payment.transaction_id = wallet_transaction.transaction_id
                payment.payment_status = 'success'
                payment.save()

                order.status = 'confirmed'
                order.save()

                return render(request, 'web/order_placed.html', {'order': order})
                
            # Handling online payments
            if payment_method == 'razorpay':
                # Creating razor pay order
                razorpay_order = create_razorpay_order(order_total_amount)
                
                if 'error' not in razorpay_order and razorpay_order.get('id'):
                    payment.payment_provider_order_id = razorpay_order['id']
                    payment.save()

                    context = {
                        "callback_url": request.scheme + "://" + request.get_host() + "/razorpay/callback/",
                        "razorpay_key": settings.RAZORPAY_API_KEY,
                        "order": order,
                        'provider_id': razorpay_order['id']
                    }
                    return render(request, 'web/razorpay_payment.html', context=context)
                else:
                    # Handle Razorpay error
                    error_message = razorpay_order.get('error', 'Payment initialization failed')
                    messages.error(request, f"Payment error: {error_message}")
                    return render(request, 'web/order_failed.html', {'order': order})
        

    # Handling GET request
    saved_addresses = Address.objects.filter(user=request.user)
    cart = Cart.objects.filter(user=request.user).first()

    total_amount, total_items_discount, cart_level_discount = cart.total_price()
    shipping_charge = cart.shipping_charge()
    total_discount = total_items_discount + cart_level_discount
    subtotal = total_amount + total_discount
    final_amount = total_amount + shipping_charge
    
    context.update({
        'saved_addresses': saved_addresses,
        'cart': cart,
        'subtotal': subtotal,
        'shipping_charge': shipping_charge,
        'total_discount': total_discount,
        'final_amount': final_amount
    })
    if cart.cart_items.exists():
        return render(request, 'web/checkout.html', context=context)
    else:
        return redirect('cart')


@csrf_exempt
def razorpay_callback(request):
    """RazorPay callback funtion. Process success or failed payments."""
    if request.method == 'GET':
        return redirect('404')
    
    if "razorpay_signature" in request.POST:
        payment_id = request.POST.get("razorpay_payment_id", "")
        razorpay_order_id = request.POST.get("razorpay_order_id", "")
        # signature_id = request.POST.get("razorpay_signature", "")

        payment_instance = Payment.objects.filter(payment_provider_order_id=razorpay_order_id).first()
        payment_instance.transaction_id = payment_id
        payment_instance.save()

        if verify_razorpay_signature(request.POST):
            payment_instance.payment_status = 'success'
            payment_instance.save()

            # Update order status to 'Confirmed'
            payment_instance.order.status = 'confirmed'
            payment_instance.order.save()

            return render(request, 'web/order_placed.html', {'order': payment_instance.order})
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
    """Retry payment fuction for payment failed orders."""
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = Order.objects.filter(order_id=order_id, user=request.user).first()

        razorpay_order = create_razorpay_order(order.total_amount)
        if 'error' not in razorpay_order and razorpay_order.get('id'):
            Payment.objects.create(
                order=order,
                amount=order.total_amount,
                payment_method='razorpay',
                payment_provider_order_id=razorpay_order['id']
            )
            context = {
                "callback_url": request.scheme + "://" + request.get_host() + "/razorpay/callback/",
                "razorpay_key": settings.RAZORPAY_API_KEY,
                "order": order,
                'provider_id': razorpay_order['id']
            }
            return render(request, 'web/razorpay_payment.html', context=context)
        else:
            # Handle Razorpay error
            error_message = razorpay_order.get('error', 'Payment initialization failed')
            messages.error(request, f"Payment error: {error_message}")
            return render(request, 'web/order_failed.html', {'order': order})

    return redirect('404')


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def update_order_status(request):
    """Update order status from Admin Panel."""
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
                
                # Bulk update order items
                order_items = list(order.order_items.all())
                for item in order_items:
                    item.status = new_status
                
                OrderItem.objects.bulk_update(order_items, ['status'])

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


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_cancel_order(request):
    """User side order cancellation function."""
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
            order_total_amount = order.total_amount + order.shipping_charge
            if payment:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += order_total_amount
                wallet.save(update_fields=["balance"])

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    transaction_id=uuid.uuid4(),
                    amount=order_total_amount,
                    status='success',
                    order=order,
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


@login_required(login_url='404')
@user_passes_test(lambda user : not user.is_blocked, login_url='404',redirect_field_name=None)
def user_return_order(request):
    """User side order return request handling."""
    if request.method == 'POST':
        order_item_id = request.POST.get('order-item-id')
        return_reason = request.POST.get('return-reason')

        order_item = OrderItem.objects.filter(id=order_item_id, order__user=request.user).first()
        if not order_item:
            return redirect('404')
        
        ReturnRequest.objects.create(
            order_item=order_item,
            reason=return_reason
        )
        order_item.status = 'return_requested'
        order_item.save()

        messages.success(request, f"We have received your return request for {order_item.product.name} order. Once the request is approved, you will receive an email with instructions on how to return.")
                
        return redirect(reverse('user_view_order', kwargs={'order_id':order_item.order.order_id}))
    
    return redirect('404')


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def process_return_request(request):
    """Processing order return requests from Admin Panel."""
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

            return_request = ReturnRequest.objects.select_related('order_item', 'order_item__order').filter(id=request_id).first()
            if return_request:
                # Update stock and refund if return is received
                if new_status == 'received':
                    with transaction.atomic():
                        return_request.status = new_status
                        return_request.order_item.status = 'return_received'

                        # Refunding amount to wallet
                        payment = return_request.order_item.order.payments.filter(payment_status='success').first()
                        
                        if payment:
                            wallet, _ = Wallet.objects.get_or_create(user=return_request.order_item.order.user)
                            wallet.balance += return_request.order_item.total_amount
                            wallet.save(update_fields=["balance"])

                            WalletTransaction.objects.create(
                                wallet=wallet,
                                transaction_type='refund',
                                transaction_id=uuid.uuid4(),
                                amount=return_request.order_item.total_amount,
                                status='success',
                                order=return_request.order_item.order,
                                notes=f"Refund for returned {return_request.order_item.product} - {return_request.order_item.variant} {return_request.order_item.product.unit} (Qty:{return_request.order_item.quantity}) from order {return_request.order_item.order.order_id}"
                            )
                            
                        # Updating stock
                        return_request.order_item.product.stock += return_request.order_item.variant * return_request.order_item.quantity
                        return_request.order_item.product.save()

                        return_request.order_item.status = 'refunded'
                        return_request.order_item.save(update_fields=["status"])

                        # Update order status if there is no other order items
                        if not return_request.order_item.order.order_items.exclude(id=return_request.order_item.id).exists():
                            return_request.order_item.order.status = 'refunded'
                            return_request.order_item.order.save()
                        
                        return_request.status = 'refunded'
                        return_request.save(update_fields=["status"])

                        return JsonResponse({
                            'success': True,
                            'message': "Return status and stock updated. Order item amount has been refunded to user's wallet."
                        })

                # Handling other statuses
                elif new_status == 'approved':
                    with transaction.atomic():
                        return_request.status = new_status
                        return_request.save(update_fields=["status"])
                        return_request.order_item.status = 'return_approved'
                        return_request.order_item.save(update_fields=["status"])
                
                elif new_status == 'rejected':
                    with transaction.atomic():
                        return_request.status = new_status
                        return_request.save(update_fields=["status"])
                        return_request.order_item.status = 'return_rejected'
                        return_request.order_item.save(update_fields=["status"])

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


def cancel_old_pending_orders():
    """Automatically cancels pending orders older than 3 days."""
    threshold_date = timezone.now() - datetime.timedelta(days=3)
    orders_to_cancel = Order.objects.filter(status="pending", order_date__lte=threshold_date)

    with transaction.atomic():
        products_to_update = {}

        for order in orders_to_cancel:
            for item in order.order_items.all():
                if item.product in products_to_update:
                    products_to_update[item.product] += item.variant * item.quantity  # Correct stock restoration
                else:
                    products_to_update[item.product] = item.variant * item.quantity

        # Bulk update all affected products in one go
        for product, quantity in products_to_update.items():
            product.stock += quantity

        Product.objects.bulk_update(products_to_update.keys(), ["stock"])

        # Bulk update order status after stock adjustments
        orders_to_cancel.update(status="cancelled")

