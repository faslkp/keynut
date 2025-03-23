from django.contrib import admin

from . models import Offer, Coupon


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'offer_type', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active')
    search_fields = ('name',)
    list_filter = ('offer_type', 'discount_type', 'is_active')
    

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'start_date', 'end_date')
    search_fields = ('code',)
    list_filter = ('discount_type', 'is_active')
