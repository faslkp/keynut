from django.urls import path

from . import views


urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('recover/', views.admin_recover_password, name='admin_recover_password'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.customers, name='products'),
    path('customers/', views.customers, name='customers'),
    path('customers/<int:pk>/blocking/', views.cutomer_blocking, name='cutomer_blocking'),
    path('orders/', views.customers, name='orders'),
    path('reports/', views.customers, name='reports'),
    path('coupons/', views.customers, name='coupons'),
    path('settings/', views.customers, name='settings'),
]
