from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('products/', views.products, name='products'),
    path('products/<str:slug>/', views.product_details, name='product_details'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('recover/', views.recover, name='recover'),
    path('register/', views.register, name='register'),
]