from django.contrib import admin

from . models import Order, OrderItem, OrderAddress, Payment


admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderAddress)
admin.site.register(Payment)