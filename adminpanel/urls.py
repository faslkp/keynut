from django.urls import path

from . import views
from products.views import add_product, edit_product, add_stock, unlist_product, add_category, edit_category, delete_category
from customers.views import add_customer, edit_customer, cutomer_blocking
from orders.views import update_order_status, process_return_request
from promotions.views import add_offer, add_coupon

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('recover/', views.admin_recover_password, name='admin_recover_password'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.products, name='admin_products'),
    path('products/add/', add_product, name='add_product'),
    path('products/<int:pk>/edit/', edit_product, name='edit_product'),
    path('products/<int:pk>/add-stock/', add_stock, name='add_stock'),
    path('products/<int:pk>/unlist/', unlist_product, name='unlist_product'),
    path('product-variants/', views.dashboard, name='admin_product_variants'),
    path('categories/', views.categories, name='admin_categories'),
    path('categories/add/', add_category, name='add_category'),
    path('categories/<int:pk>/edit/', edit_category, name='edit_category'),
    path('categories/<int:pk>/delete/', delete_category, name='delete_category'),
    path('customers/', views.customers, name='admin_customers'),
    path('customers/add/', add_customer, name='add_customer'),
    path('customers/<int:pk>/edit/', edit_customer, name='edit_customer'),
    path('customers/<int:pk>/block/', cutomer_blocking, name='cutomer_blocking'),
    path('orders/', views.orders, name='admin_orders'),
    path('orders/<str:order_id>/view/', views.view_order_details, name='admin_view_order_details'),
    path('orders/update-status/', update_order_status, name='update_order_status'),
    path('returns/', views.return_requests, name='admin_returns'),
    path('returns/update-status/', process_return_request, name='update_return_status'),
    path('reports/', views.reports, name='admin_reports'),
    path('offers/', views.offers, name='admin_offers'),
    path('offers/add/', add_offer, name='add_offer'),
    path('coupons/', views.coupons, name='admin_coupons'),
    path('coupons/add/', add_coupon, name='add_coupon'),
    path('wallet-transactions/', views.wallet_transactions, name='admin_wallet_transactions'),
    path('settings/', views.dashboard, name='admin_settings'),
    path('unavailable/', views.unavailable, name='unavailable'),
]
