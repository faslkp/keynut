import random
import datetime
import csv
import tempfile
import json

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login as authlogin, logout as authlogout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import F, Q, Subquery, OuterRef, Sum, DecimalField, Value, IntegerField
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Coalesce
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.db.models import Count
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models.functions import TruncDate

from weasyprint import HTML

from customers.forms import CustomerForm
from customers.models import WalletTransaction, Message
from products.forms import ProductForm, CategoryForm, VariantForm
from products.models import Product, ProductVariant, Category
from orders.models import Order, OrderItem, Payment, ReturnRequest
from promotions.models import Offer, Coupon
from promotions.forms import OfferForm, CouponForm
from orders.views import cancel_old_pending_orders

User = get_user_model()

@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def dashboard(request):
    """Generate sales data to display on Admin panel dashboard."""

    # Cancel all pending orders before 3 days
    cancel_old_pending_orders()

    # Get all order details and top selling products and categories
    orders = Order.objects.prefetch_related('order_items').filter(
        ~Q(status='pending') & ~Q(status='refunded') & ~Q(status='cancelled')
    ).annotate(
        date_of_order=TruncDate('order_date')
    ).values('date_of_order').annotate(
        total_sales=Sum(F('order_item__price') * F('order_item__variant') * F('order_item__quantity'))
    ).order_by('date_of_order')

    top_selling_products = (
        OrderItem.objects.filter(
            ~Q(order__status='pending') & ~Q(order__status='refunded') & ~Q(order__status='cancelled')
        )
        .values('product__name', 'product__unit')
        .annotate(total_sales=Sum(F('variant') * F('quantity')))
        .order_by('-total_sales')
    )

    top_selling_categories = (
        OrderItem.objects.filter(
            ~Q(order__status='pending') & ~Q(order__status='refunded') & ~Q(order__status='cancelled')
        )
        .values('product__category__name')
        .annotate(total_sales=Sum(F('variant') * F('quantity')))
        .order_by('-total_sales')
    )

    # Get recent orders
    recent_orders = Order.objects.prefetch_related('order_items', 'payments').filter(
        ~Q(status='pending') & ~Q(status='cancelled') & ~Q(status='refunded')
    ).annotate(
        order_total_amount=ExpressionWrapper(
            Sum(F('order_item__variant') * F('order_item__quantity') * F('order_item__price')),
            output_field=DecimalField()
        ),
        payment_method=Coalesce(
            # If there is a Success payment, getting it
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'), payment_status='success')
                .order_by('-payment_date')
                .values('payment_method')[:1]
            ),
            # If there is no Success payment, getting latest payment details
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'))
                .order_by('-payment_date')
                .values('payment_method')[:1]
            ),
        ),
        payment_status=Coalesce(
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'), payment_status='success')
                .order_by('-payment_date')
                .values('payment_status')[:1]
            ),
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'))
                .order_by('-payment_date')
                .values('payment_status')[:1]
            ),
        )
    ).order_by('-order_date')

    # Handling filters
    filter_value = request.GET.get('filter')
    start_date = request.GET.get('start-date')
    end_date = request.GET.get('end-date')

    today = datetime.datetime.today().date()
    start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
    end_of_week = start_of_week + datetime.timedelta(days=6)
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    if filter_value:
        match filter_value:
            case "today":
                orders = orders.filter(order_date__date=today)
                top_selling_products = top_selling_products.filter(order__order_date__date=today)
                top_selling_categories = top_selling_categories.filter(order__order_date__date=today)
                recent_orders = recent_orders.filter(order_date__date=today)
            case "yesterday":
                orders = orders.filter(order_date__date=today - datetime.timedelta(days=1))
                top_selling_products = top_selling_products.filter(order__order_date__date=today - datetime.timedelta(days=1))
                top_selling_categories = top_selling_categories.filter(order__order_date__date=today - datetime.timedelta(days=1))
                recent_orders = recent_orders.filter(order_date__date=today - datetime.timedelta(days=1))
            case "this-week":
                orders = orders.filter(order_date__date__range=(start_of_week, end_of_week))
                top_selling_products = top_selling_products.filter(order__order_date__range=(start_of_week, end_of_week))
                top_selling_categories = top_selling_categories.filter(order__order_date__range=(start_of_week, end_of_week))
                recent_orders = recent_orders.filter(order_date__date__range=(start_of_week, end_of_week))
            case "this-month":
                orders = orders.filter(order_date__date__gte=start_of_month)
                top_selling_products = top_selling_products.filter(order__order_date__gte=start_of_month)
                top_selling_categories = top_selling_categories.filter(order__order_date__gte=start_of_month)
                recent_orders = recent_orders.filter(order_date__date__gte=start_of_month)
            case "this-year":
                orders = orders.filter(order_date__date__gte=start_of_year)
                top_selling_products = top_selling_products.filter(order__order_date__gte=start_of_year)
                top_selling_categories = top_selling_categories.filter(order__order_date__gte=start_of_year)
                recent_orders = recent_orders.filter(order_date__date__gte=start_of_year)
            case "all-time":
                orders = orders
                top_selling_products = top_selling_products
                top_selling_categories = top_selling_categories
                recent_orders = recent_orders
        
    # Custom date range filtering
    if start_date and end_date:
        orders = orders.filter(order_date__date__range=(start_date, end_date))
        top_selling_products = top_selling_products.filter(order__order_date__date__range=(start_date, end_date))
        top_selling_categories = top_selling_categories.filter(order__order_date__date__range=(start_date, end_date))
        recent_orders = recent_orders.filter(order_date__date__range=(start_date, end_date))
    
    elif start_date:
        orders = orders.filter(order_date__gte=start_date)
        top_selling_products = top_selling_products.filter(order__order_date__gte=start_date)
        top_selling_categories = top_selling_categories.filter(order__order_date__gte=start_date)
        recent_orders = recent_orders.filter(order_date__gte=start_date)
    
    elif end_date:
        orders = orders.filter(order_date__lte=end_date)
        top_selling_products = top_selling_products.filter(order__order_date__lte=end_date)
        top_selling_categories = top_selling_categories.filter(order__order_date__lte=end_date)
        recent_orders = recent_orders.filter(order_date__lte=end_date)

    # Filter by current week data by default
    if not filter_value and not start_date and not end_date:
        orders = orders.filter(order_date__date__range=(start_of_week, end_of_week))
        top_selling_products = top_selling_products.filter(order__order_date__range=(start_of_week, end_of_week))
        top_selling_categories = top_selling_categories.filter(order__order_date__range=(start_of_week, end_of_week))
        recent_orders = recent_orders.filter(order_date__date__range=(start_of_week, end_of_week))

    # Perform aggregation to get sales data
    reports = recent_orders.aggregate(
        total_sales=Coalesce(Sum('order_total_amount'), Value(0), output_field=DecimalField()),
        total_orders=Coalesce(Count('order_id', distinct=True), Value(0), output_field=IntegerField())
    )

    average_order_value = reports["total_sales"] / reports["total_orders"] if reports["total_orders"] > 0 else 0

    total_products_sold = OrderItem.objects.filter(order__in=recent_orders).aggregate(
        total=Sum(ExpressionWrapper(F('quantity') * F('variant'), output_field=DecimalField()))
    )['total'] or 0

    reports['total_products_sold'] = total_products_sold
    reports['average_order_value'] = average_order_value
    

    context = {
        'orders': orders,
        'top_selling_products': top_selling_products[:10],
        'top_selling_categories': top_selling_categories[:10],
        'recent_orders': recent_orders[:15],
        'reports': reports,
    }
    return render(request, 'admin/dashboard.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def products(request):
    """Fetch all products data to display in Admin Panel Products page."""
    products = Product.objects.select_related('category').filter(is_deleted=False).order_by("-created_at")
    
    # Handle sort, filter, category and search
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    category = request.GET.get('category')
    q = request.GET.get('q')

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
    paginator = Paginator(products, 10) #10 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    categories = Category.objects.all()
    form = ProductForm()

    context = {
        'products': products,
        'categories': categories,
        'form': form
    }
    return render(request, 'admin/products.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def product_variants(request):
    """Fetch all products variants data to display in Admin Panel Product Variants page."""
    variants = ProductVariant.objects.all().order_by('quantity')

    # Handle sort and search
    sortby = request.GET.get('sortby')
    if sortby:
        variants = variants.order_by(sortby)
    
    q = request.GET.get('q')
    if q:
        variants = variants.filter(quantity__iexact=q)

    # Pagination
    paginator = Paginator(variants, 10)
    page_number = request.GET.get('page')
    variants = paginator.get_page(page_number)

    form = VariantForm()

    context = {
        'variants': variants,
        'form': form,
    }
    return render(request, 'admin/product_variants.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def categories(request):
    """Fetch all categories data to display in Admin Panel Categories page."""
    categories = Category.objects.all().order_by("-created_at")
    
    # Handle sort, filter, category and search
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')

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
    paginator = Paginator(categories, 10) #10 categories per page
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)

    form = CategoryForm()

    context = {
        'categories': categories,
        'form': form
    }
    return render(request, 'admin/categories.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def customers(request):
    """Fetch all customers data to display in Admin Panel Customers page."""
    context = {}
    customers = User.objects.filter(is_staff=False).order_by("-date_joined")
    
    # Handle sort, filter and search
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')

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
    paginator = Paginator(customers, 10) #10 customers per page
    page_number = request.GET.get('page')
    customers = paginator.get_page(page_number)

    form = CustomerForm()
    context = {
        'customers': customers,
        'form': form
    }
    return render(request, 'admin/customers.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def orders(request):
    """Fetch all orders data to display in Admin Panel Orders page."""
    orders = Order.objects.prefetch_related('order_items', 'payments').annotate(
        order_total_amount=ExpressionWrapper(
            Sum(F('order_item__variant') * F('order_item__quantity') * F('order_item__price')),
            output_field=DecimalField()
        ),
        payment_method=Coalesce(
            # If there is a Success payment, getting it
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'), payment_status='success')
                .order_by('-payment_date')
                .values('payment_method')[:1]
            ),
            # If there is no Success payment, getting latest payment details
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'))
                .order_by('-payment_date')
                .values('payment_method')[:1]
            ),
        ),
        payment_status=Coalesce(
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'), payment_status='success')
                .order_by('-payment_date')
                .values('payment_status')[:1]
            ),
            Subquery(
                Payment.objects.filter(order=OuterRef('pk'))
                .order_by('-payment_date')
                .values('payment_status')[:1]
            ),
        )
    ).order_by('-order_date')

    # Handle sort, filter, search
    sortby = request.GET.get('sortby')
    filter_order_status = request.GET.get('order-status')
    filter_pay_status = request.GET.get('pay-status')
    filter_pay_method = request.GET.get('pay-method')
    q = request.GET.get('q')

    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            orders = orders.order_by(Lower(field_name).desc())
        else:
            orders = orders.order_by(sortby)
    
    if filter_order_status:
        orders = orders.filter(status=filter_order_status)
    
    if filter_pay_status:
        orders = orders.filter(payment_status=filter_pay_status)
    
    if filter_pay_method:
        orders = orders.filter(payment_method=filter_pay_method)
    
    if q:
        orders = orders.filter(Q(order_id__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q))

    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    status_choices = dict(Order.STATUS_CHOICES)
    payment_methods = dict(Payment.PAYMENT_METHODS)

    context = {
        'orders': orders,
        'order_status': Order.STATUS_CHOICES,
        'status_choices': status_choices,
        'payment_methods': payment_methods,
    }
    return render(request, 'admin/orders.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def view_order_details(request, order_id):
    """Fetch all details of an order for Admin Panel."""
    order = Order.objects.filter(order_id=order_id).first()
    order_items = OrderItem.objects.filter(order=order).values(
        'product__name', 'price', 'product__unit', 'variant', 'quantity', 'status'
    )
    payments = Payment.objects.filter(order=order).values(
        'payment_date', 'amount', 'payment_status', 'payment_method', 'transaction_id'
    )

    # If order or order items not found, return error
    if not order or not order_items:
        return JsonResponse({
        'error': True,
        'message': 'Order details not found.'
    })

    # Manually add total_amount to each item
    for item in order_items:
        item["total_amount"] = item["variant"] * item["quantity"] * item["price"]

    # Getting order status choices
    statuses = order.get_next_statuses()
    status_choices = [choice for choice in Order.STATUS_CHOICES if choice[0] in statuses or choice[0] == order.status]

    return JsonResponse({
        'success': True,
        'message': 'Order details fetched successfully.',
        'id': order.id,
        'order_id': order.order_id,
        'order_date': order.order_date,
        'address': model_to_dict(order.delivery_address),
        'status': order.status,
        'total_amount': order.total_amount,
        'order_items': list(order_items),
        'payments': list(payments),
        'status_choices': status_choices,
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def return_requests(request):
    """Fetch all return requests for Admin Panel Return Requests page."""
    return_requests = ReturnRequest.objects.select_related(
        'order_item').annotate(
            item_total_amount=ExpressionWrapper(
                Sum(F('order_item__variant') * F('order_item__quantity') * F('order_item__price')),
                output_field=DecimalField()
            ),
            payment_method=Coalesce(
                # If there is a Success payment, getting it
                Subquery(
                    Payment.objects.filter(order=OuterRef('order_item__order'), payment_status='success')
                    .order_by('-payment_date')
                    .values('payment_method')[:1]
                ),
                # If there is no Success payment, getting latest payment details
                Subquery(
                    Payment.objects.filter(order=OuterRef('order_item__order'))
                    .order_by('-payment_date')
                    .values('payment_method')[:1]
                ),
            ),
        ).order_by('-created_at')

    # Handle sort, filter and search
    sortby = request.GET.get('sortby')
    filter_status = request.GET.get('status')
    q = request.GET.get('q')

    if sortby:
        return_requests = return_requests.order_by(sortby)

    if filter_status:
        return_requests = return_requests.filter(status=filter_status)

    if q:
        return_requests = return_requests.filter(
            Q(order__order_id__icontains=q) | Q(order__user__email__icontains=q) |
            Q(order__user__first_name__icontains=q) | Q(order__user__last_name__icontains=q))
        
    # Pagination
    paginator = Paginator(return_requests, 10)
    page_number = request.GET.get('page')
    return_requests = paginator.get_page(page_number)
    
    payment_methods = dict(Payment.PAYMENT_METHODS)
    status_choices = dict(ReturnRequest.RETURN_STATUS_CHOICES)
    
    context = {
        'return_requests': return_requests,
        'status_choices': status_choices,
        'payment_methods': payment_methods,
    }
    return render(request, 'admin/return_requests.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def customer_messages(request):
    """Fetch all messages from Contact Form to Admin Panel Messages page.

    Using POST request to update status of any specific message.
    """
    # Handle message status updation if POST request
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_id = data.get("message_id")
            new_status = data.get("status")

            if not new_status:
                return JsonResponse({
                    'error': True,
                    'message': "Nothing to update!"
                })

            message = Message.objects.filter(id=message_id).first()
            if message:
                message.status = new_status
                message.save(update_fields=["status"])

                return JsonResponse({
                    'success': True,
                    'message': "Message status updated successfully."
                })
            else:
                return JsonResponse({
                    'error': True,
                    'message': "Message not found!"
                })
        
        except Exception as e:
            return JsonResponse({'error': True, "message": str(e)})

    # Fetch all messages if GET request
    all_messages = Message.objects.all().order_by('-created_at')

    # Handle sort, filter, and search
    sortby = request.GET.get('sortby')
    filter_status = request.GET.get('status')
    q = request.GET.get('q')

    if sortby:
        all_messages = all_messages.order_by(sortby)

    if filter_status:
        all_messages = all_messages.filter(status=filter_status)

    if q:
        all_messages = all_messages.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(message__icontains=q) | 
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q))

    # Pagination
    paginator = Paginator(all_messages, 10)
    page_number = request.GET.get('page')
    all_messages = paginator.get_page(page_number)

    status_choices = Message.STATUS_CHOICES
    context = {
        'all_messages': all_messages,
        'status_choices': status_choices,
    }
    return render(request, 'admin/messages.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def view_customer_message(request, pk):
    """Fetch full details of a message."""
    message = Message.objects.filter(pk=pk).first()

    # Update status to 'open' when message is opened.
    message.status = 'open'
    message.save()

    # Handle invalid request
    if not message:
        return JsonResponse({
            'error': True,
            'message': 'Message not found!'
        })
    
    return JsonResponse({
        'success': True,
        'message': 'Message details fetched successfully.',
        'message_date': message.created_at,
        'message_user': message.user.email if message.user else None,
        'message_name': message.name,
        'message_email': message.email,
        'message_phone': message.phone,
        'message_message': message.message
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def offers(request):
    """Fetch all offers for Admin Panel Offers page."""
    offers = Offer.objects.all().order_by('-start_date')

    # Handle sort, filter, and search
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')
    
    # Handle sort, filter, category and search
    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            offers = offers.order_by(Lower(field_name).desc())
        else:
            offers = offers.order_by(sortby)
    
    if filter:
        match filter:
            case "active":
                offers = offers.filter(start_date__lte=datetime.datetime.now(), end_date__gte=datetime.datetime.now())
            case "upcoming":
                offers = offers.filter(start_date__gt=datetime.datetime.now())
            case "expired":
                offers = offers.filter(end_date__lt=datetime.datetime.now())
    
    if q:
        offers = offers.filter(name__icontains=q)
    
    # Pagination
    paginator = Paginator(offers, 10) #10 offers per page
    page_number = request.GET.get('page')
    offers = paginator.get_page(page_number)

    form = OfferForm()

    context = {
        'offers': offers,
        'form': form,
    }
    return render(request, 'admin/offers.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def coupons(request):
    """Fetch all coupons for Admin Panel Coupons page."""
    coupons = Coupon.objects.all().order_by('-start_date')

    # Handle sort, filter, and search
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')
    
    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            coupons = coupons.order_by(Lower(field_name).desc())
        else:
            coupons = coupons.order_by(sortby)
    
    if filter:
        match filter:
            case "active":
                coupons = coupons.filter(start_date__lte=datetime.datetime.now(), end_date__gte=datetime.datetime.now(), is_active=True)
            case "disabled":
                coupons = coupons.filter(is_active=False)
            case "percentage":
                coupons = coupons.filter(discount_type='percentage')
            case "flat":
                coupons = coupons.filter(discount_type='flat')
            case "cart":
                coupons = coupons.filter(apply_to_total_order=True)
            case "product":
                coupons = coupons.filter(products__isnull=False)
            case "category":
                coupons = coupons.filter(categories__isnull=False)
            case "user":
                coupons = coupons.filter(users__isnull=False)
    
    if q:
        coupons = coupons.filter(Q(code__icontains=q) | Q(description__icontains=q))
    
    # Pagination
    paginator = Paginator(coupons, 10) #10 coupons per page
    page_number = request.GET.get('page')
    coupons = paginator.get_page(page_number)

    form = CouponForm()
    context = {
        'coupons': coupons,
        'form': form
    }
    return render(request, 'admin/coupons.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def wallet_transactions(request):
    """Fetch all wallet transactions for Admin Panel Wallet Transactions page."""
    transactions = WalletTransaction.objects.all().order_by('-created_at')

    # Sort, filter, search
    sortby = request.GET.get('sortby')
    filter_status = request.GET.get('status')
    q = request.GET.get('q')

    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            transactions = transactions.order_by(Lower(field_name).desc())
        else:
            transactions = transactions.order_by(sortby)
    
    if filter_status:
        transactions = transactions.filter(status=filter_status)
    
    if q:
        transactions = transactions.filter(Q(wallet__user__first_name__icontains=q) | Q(wallet__user__last_name__icontains=q) | Q(order__order_id__icontains=q) | Q(transaction_id__icontains=q) | Q(amount__iexact=q))

    # Pagination
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    context = {
        'transactions': transactions
    }
    return render(request, 'admin/wallet_transactions.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def ledger_book(request):
    """Fetch all success payment transactions - credit and debit to compay - including cash transactions."""
    transactions = Payment.objects.filter(~Q(payment_method='wallet') & Q(payment_status='success')).order_by('-payment_date')

    # Sort, filter, search
    sortby = request.GET.get('sortby')
    filter_type = request.GET.get('type')
    q = request.GET.get('q')

    if sortby:
        if sortby.startswith('-'):
            field_name = sortby.lstrip('-')
            transactions = transactions.order_by(Lower(field_name).desc())
        else:
            transactions = transactions.order_by(sortby)
    
    if filter_type:
        transactions = transactions.filter(payment_type=filter_type)
    
    if q:
        transactions = transactions.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(order__order_id__icontains=q) | Q(transaction_id__icontains=q) | Q(amount__iexact=q))
        
    # Pagination
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)

    context = {
        'transactions': transactions
    }
    return render(request, 'admin/ledger_book.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def reports(request):
    """Fetch all sales data for generating sales reports.
    
    Reports are served in Admin Panel Reports page, CSV file, and PDF file.
    """
    today = datetime.datetime.today().date()
    start_of_week = today - datetime.timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
    end_of_week = start_of_week + datetime.timedelta(days=6)
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    # Initial filtering
    base_query = OrderItem.objects.select_related('order').prefetch_related('product').filter(
        ~Q(order__status='pending') & ~Q(order__status='refunded') & ~Q(order__status='cancelled')
    )

    order_items = base_query.annotate(total_quantity=F('variant') * F('quantity')).order_by('-order__order_date')

    # Handling filters
    filter_value = request.GET.get('filter')
    start_date = request.GET.get('start-date')
    end_date = request.GET.get('end-date')

    if filter_value:
        match filter_value:
            case "today":
                order_items = order_items.filter(order__order_date__date=today)
            case "yesterday":
                order_items = order_items.filter(order__order_date__date=today - datetime.timedelta(days=1))
            case "this-week":
                order_items = order_items.filter(order__order_date__date__range=(start_of_week, end_of_week))
            case "this-month":
                order_items = order_items.filter(order__order_date__date__gte=start_of_month)
            case "this-year":
                order_items = order_items.filter(order__order_date__date__gte=start_of_year)
            case "all-time":
                order_items = order_items

    # Custom date range filtering
    if start_date and end_date:
        end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        order_items = order_items.filter(order__order_date__range=[start_date, end_date_obj])
    elif start_date:
        order_items = order_items.filter(order__order_date__gte=start_date)
    elif end_date:
        end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        order_items = order_items.filter(order__order_date__lte=end_date_obj)

    # Filter by this-week by default if none is selected
    if not filter_value and not start_date and not end_date:
        order_items = order_items.filter(order__order_date__date__range=(start_of_week, end_of_week))

    # Perform aggregation to get sales data figures
    reports = order_items.aggregate(
        total_sales=Coalesce(Sum(F('variant') * F('quantity') * F('price')), Value(0), output_field=DecimalField()),
        total_orders=Coalesce(Count('order', distinct=True), Value(0), output_field=IntegerField()),
        total_products_sold=Coalesce(Sum(F('quantity') * F('variant')), Value(0), output_field=DecimalField())
    )

    average_order_value = reports["total_sales"] / reports["total_orders"] if reports["total_orders"] > 0 else 0
    reports['average_order_value'] = average_order_value

    # Handle download
    download = request.GET.get('download')
    if download:
        # CSV file download
        if download == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="reports.csv"'

            writer = csv.writer(response)
            writer.writerow(['Total Sales', 'Total Orders', 'Total Products Sold', 'Average Order Value'])
            writer.writerow([reports['total_sales'], reports['total_orders'], reports['total_products_sold'], reports['average_order_value']])
            writer.writerow([])
            writer.writerow(['Product Name', 'Category', 'Price', 'Variant', 'Quantity', 'Total Quantity', 'Item Price', 'Total Amount', 'Order ID', 'Order Date', 'Order Status'])
            for item in order_items:
                writer.writerow([
                    item.product.name,
                    item.product.category.name,
                    item.product.price,
                    item.variant,
                    item.quantity,
                    item.total_quantity,
                    item.price,
                    item.total_amount,
                    item.order.order_id,
                    item.order.order_date,
                    item.order.status,
                ])
            return response
        
        # PDF file download
        elif download == 'pdf':
            # Getting date range string to display in PDF
            if filter_value:
                match filter_value:
                    case "today":
                        filter_value = datetime.datetime.today().strftime("%d %B, %Y")
                    case "yesterday":
                        filter_value = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%d %B, %Y")
                    case "this-week":
                        filter_value = f"{start_of_week.strftime('%d %B, %Y')} - {end_of_week.strftime('%d %B, %Y')}"
                    case "this-month":
                        filter_value = datetime.datetime.today().strftime("%B, %Y")
                    case "this-year":
                        filter_value = datetime.datetime.today().strftime("%Y")
            elif start_date and end_date:
                filter_value = f"{start_date} - {end_date}"
            elif start_date:
                filter_value = f"Since {start_date}"
            elif end_date:
                filter_value = f"Until {end_date}"

            # Setting context values for PDF
            pdf_context = {
                'reports': reports,
                'order_items': order_items,
                'filter_value': filter_value
            }

            # Setting HTML string
            html_string = render_to_string("admin/reports_pdf.html", context=pdf_context)

            # Generate PDF
            html = HTML(string=html_string)
            pdf_file = tempfile.NamedTemporaryFile(delete=True)
            html.write_pdf(target=pdf_file.name)

            # Serve the file as response
            with open(pdf_file.name, "rb") as pdf:
                response = HttpResponse(pdf.read(), content_type="application/pdf")
                response["Content-Disposition"] = f'attachment; filename="reports.pdf"'
                return response

    # Pagination
    paginator = Paginator(order_items, 10)
    page_number = request.GET.get('page')
    order_items = paginator.get_page(page_number)

    context = {
        'reports': reports,
        'order_items': order_items
    }
    return render(request, 'admin/reports.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def settings(request):
    """Admin Panel settings.

    POST request updates admin user password.
    """
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
    return render(request, 'admin/settings.html')


@user_passes_test(lambda user: not user.is_authenticated, login_url='dashboard',redirect_field_name=None)
def admin_login(request):
    """Admin login - authenticate using username and password. Verify if user is staff."""
    context = {}
    if request.POST:
        email = request.POST['email']
        password = request.POST['password']
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
    """Admin user password recovery - Forgot password.

    Verify user with OTP on email.
    """
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
            generated_timestamp = request.session.get('otp_timestamp')

            if generated_timestamp:
                generated_timestamp = datetime.datetime.fromisoformat(generated_timestamp)
                if (datetime.datetime.now() - generated_timestamp).seconds < 300:
                    messages.error(request, "Please wait while OTP reaches your inbox. If not received within 5 minutes, please click 'Resend OTP'.")
                    context.update({'stage': 'otp', 'email': email})
                else:
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
    """Admin user logout."""
    authlogout(request)
    return redirect('admin_login')


def unavailable(requset):
    """404 page for unavailable page requests or access restricted page requests."""
    return render(requset, 'admin/unavailable_404.html')