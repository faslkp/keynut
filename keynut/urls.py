from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('superadmin/', admin.site.urls),
    path('admin/', include('adminpanel.urls')),
    path('customers/', include('customers.urls')),
]
