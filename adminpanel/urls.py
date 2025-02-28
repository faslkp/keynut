from django.urls import path

from . views import dashboard, admin_login, admin_logout, admin_recover_password


urlpatterns = [
    path('login/', admin_login, name='admin_login'),
    path('recover/', admin_recover_password, name='admin_recover_password'),
    path('logout/', admin_logout, name='admin_logout'),
    path('', dashboard, name='dashboard'),
]
