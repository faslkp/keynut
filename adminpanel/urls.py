from django.urls import path

from . import views
from products.views import add_product, edit_product, unlist_product
from customers.views import add_customer, edit_customer, cutomer_blocking

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('recover/', views.admin_recover_password, name='admin_recover_password'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.products, name='products'),
    path('products/add/', add_product, name='add_product'),
    path('products/<int:pk>/edit/', edit_product, name='edit_product'),
    path('products/<int:pk>/unlist/', unlist_product, name='unlist_product'),
    path('customers/', views.customers, name='customers'),
    path('customers/add/', add_customer, name='add_customer'),
    path('customers/<int:pk>/edit/', edit_customer, name='edit_customer'),
    path('customers/<int:pk>/block/', cutomer_blocking, name='cutomer_blocking'),
    path('orders/', views.customers, name='orders'),
    path('reports/', views.customers, name='reports'),
    path('coupons/', views.customers, name='coupons'),
    path('settings/', views.customers, name='settings'),
]
