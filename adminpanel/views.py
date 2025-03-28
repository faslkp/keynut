import random
import datetime
import csv
import tempfile

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login as authlogin, logout as authlogout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import F, Q, Subquery, OuterRef, Sum, DecimalField
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
from customers.models import WalletTransaction
from products.forms import ProductForm, CategoryForm
from products.models import Product, Category
from orders.models import Order, OrderItem, Payment, ReturnRequest
from promotions.models import Offer, Coupon
from promotions.forms import OfferForm, CouponForm

User = get_user_model()

@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def dashboard(request):
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


    # Perform aggregation
    reports = recent_orders.aggregate(
        total_sales=Sum('order_total_amount'),
        total_orders=Count('order_id', distinct=True),
        average_order_value=ExpressionWrapper(
            Coalesce(Sum('order_total_amount'), 0) /
            Coalesce(Count('order_id', distinct=True), 1),
            output_field=DecimalField()
        )
    )

    total_products_sold = OrderItem.objects.filter(order__in=recent_orders).aggregate(
        total=Sum(F('quantity') * F('variant'))
    )['total'] or 0

    reports['total_products_sold'] = total_products_sold
    

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
    context = {}
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    category = request.GET.get('category')
    q = request.GET.get('q')
    products = Product.objects.select_related('category').filter(is_deleted=False).order_by("-created_at")
    
    # Handle sort, filter, category and search
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

    context.update({'products': products, 'categories': categories, 'form': form})
    return render(request, 'admin/products.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def categories(request):
    context = {}
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')
    categories = Category.objects.all().order_by("-created_at")
    
    # Handle sort, filter, category and search
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

    context.update({'categories': categories, 'form': form})
    return render(request, 'admin/categories.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def customers(request):
    context = {}
    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')
    customers = User.objects.filter(is_staff=False).order_by("-date_joined")
    
    # Handle sort, filter and search
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
    context.update({'customers': customers, 'form': form})
    return render(request, 'admin/customers.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def orders(request):
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

    # getting order status choices
    disabled_statuses = ["return_requested", "return_approved", "return_rejected", "refunded", "cancelled"]
    # Exclude the disabled statuses from STATUS_CHOICES
    status_choices = [choice for choice in Order.STATUS_CHOICES if choice[0] not in disabled_statuses]

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
    order = Order.objects.filter(order_id=order_id).first()
    order_items = OrderItem.objects.filter(order=order).values(
        'product__name', 'product__price', 'product__unit', 'variant', 'quantity'
    )
    payments = Payment.objects.filter(order=order).values(
        'payment_date', 'amount', 'payment_status', 'payment_method', 'transaction_id'
    )


    # Manually add total_amount to each item
    for item in order_items:
        item["total_amount"] = item["variant"] * item["quantity"] * item["product__price"]

    if not order or not order_items:
        return JsonResponse({
        'error': True,
        'message': 'Order details not found.'
    })

    # getting order status choices
    disabled_statuses = ["return_requested", "return_approved", "return_rejected", "refunded", "cancelled"]
    if order.status in disabled_statuses:
        disabled_statuses.remove(order.status)
    # Exclude the disabled statuses from STATUS_CHOICES
    status_choices = [choice for choice in Order.STATUS_CHOICES if choice[0] not in disabled_statuses]

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
    return_requests = ReturnRequest.objects.select_related('order').prefetch_related(
        'order__order_items').annotate(
            order_total_amount=ExpressionWrapper(
                Sum(F('order__order_item__variant') * F('order__order_item__quantity') * F('order__order_item__price')),
                output_field=DecimalField()
            ),
            payment_method=Coalesce(
                # If there is a Success payment, getting it
                Subquery(
                    Payment.objects.filter(order=F('order'), payment_status='Success')
                    .order_by('-payment_date')
                    .values('payment_method')[:1]
                ),
                # If there is no Success payment, getting latest payment details
                Subquery(
                    Payment.objects.filter(order=F('order'))
                    .order_by('-payment_date')
                    .values('payment_method')[:1]
                ),
            ),
        ).order_by('-created_at')

    # Pagination
    paginator = Paginator(return_requests, 10)
    page_number = request.GET.get('page')
    return_requests = paginator.get_page(page_number)
    
    payment_methods = dict(Payment.PAYMENT_METHODS)
    status_choices = ReturnRequest.RETURN_STATUS_CHOICES
    context = {
        'return_requests': return_requests,
        'status_choices': status_choices,
        'payment_methods': payment_methods,
    }
    return render(request, 'admin/return_requests.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def offers(request):
    offers = Offer.objects.all().order_by('-start_date')

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
    coupons = Coupon.objects.all().order_by('-start_date')

    sortby = request.GET.get('sortby')
    filter = request.GET.get('filter')
    q = request.GET.get('q')
    
    # Handle sort, filter, category and search
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
    transactions = WalletTransaction.objects.all().order_by('-created_at')

    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    context = {
        'transactions': transactions
    }
    return render(request, 'admin/wallet_transactions.html', context=context)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def reports(request):
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

    # Perform aggregation
    reports = order_items.aggregate(
        total_sales=Sum(F('variant') * F('quantity') * F('price')),
        total_orders=Count('order', distinct=True),
        total_products_sold=Sum(F('quantity') * F('variant')),
        average_order_value=ExpressionWrapper(
            Coalesce(Sum(F('variant') * F('quantity') * F('price')), 0) /
            Coalesce(Count('order', distinct=True), 1),
            output_field=DecimalField()
        )
    )

    # Handle download
    download = request.GET.get('download')
    if download:
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
        
        # PDF
        elif download == 'pdf':
            # Getting date range string
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

            # Setting context values
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
    paginator = Paginator(order_items, 10) #10 coupons per page
    page_number = request.GET.get('page')
    order_items = paginator.get_page(page_number)

    context = {
        'reports': reports,
        'order_items': order_items
    }
    return render(request, 'admin/reports.html', context=context)


@user_passes_test(lambda user: not user.is_authenticated, login_url='dashboard',redirect_field_name=None)
def admin_login(request):
    context = {}
    if request.POST:
        email = request.POST['email']
        password = request.POST['password']
        print(email, password)
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
    authlogout(request)
    return redirect('admin_login')


def unavailable(requset):
    return render(requset, 'admin/unavailable_404.html')