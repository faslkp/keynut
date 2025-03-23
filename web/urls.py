from django.urls import path

from . import views
from customers.views import cart, add_to_cart, remove_from_cart, apply_coupon, wishlist, toggle_wishlist
from orders.views import checkout, user_cancel_order, user_return_order, razorpay_callback, checkout_retry

urlpatterns = [
    path('', views.index, name='index'),
    path('products/', views.products, name='products'),
    path('deals/', views.products, name='deals'),
    path('products/<str:slug>/', views.product_details, name='product_details'),
    path('wishlist/', wishlist, name='wishlist'),
    path('wishlist/<int:product_id>/toggle/', toggle_wishlist, name='toggle_wishlist'),
    path('cart/', cart, name='cart'),
    path('cart/add/', add_to_cart, name='add_to_cart'),
    path('cart/<int:pk>/remove/', remove_from_cart, name='remove_from_cart'),
    path('cart/apply-coupon/', apply_coupon, name='apply_coupon'),
    path('checkout/', checkout, name='checkout'),
    path('orders/', views.user_orders, name='user_orders'),
    path('orders/<str:order_id>/view/', views.user_view_order, name='user_view_order'),
    path('orders/<str:order_id>/invoice/', views.user_order_invoice, name='user_order_invoice'),
    path('orders/cancel-order/', user_cancel_order, name='user_cancel_order'),
    path('orders/return-order/', user_return_order, name='user_return_order'),
    path('razorpay/callback/', razorpay_callback, name='razorpay_callback'),
    path('checkout/retry/', checkout_retry, name='checkout_retry'),
    path('login/', views.login, name='login'),
    path('google-login/', views.CustomGoogleLoginView.as_view(), name='gl_login'),
    path('logout/', views.logout, name='logout'),
    path('recover/', views.recover, name='recover'),
    path('register/', views.register, name='register'),
    path('profile/update/', views.user_profile, name='user_profile'),
    path('profile/change-password/', views.user_change_password, name='user_change_password'),
    path('profile/address/', views.user_address, name='user_address'),
    path('profile/address/add/', views.user_add_address, name='user_add_address'),
    path('profile/address/<int:pk>/edit/', views.user_edit_address, name='user_edit_address'),
    path('profile/address/<int:pk>/set-default/', views.user_set_address_default, name='user_set_address_default'),
    path('profile/address/<int:pk>/delete/', views.user_delete_address, name='user_delete_address'),
    path('profile/ratings/', views.user_ratings, name='user_ratings'),
    path('404/', views.four_not_four, name='404'),
]