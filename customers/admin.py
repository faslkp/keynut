from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

from . models import Address, Wishlist, Cart, CartItem, Wallet, WalletTransaction, Subscriber

# admin.site.register(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'referral_key', 'is_verified', 'is_blocked', 'is_deleted')}),
    )

class AddressAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Address, AddressAdmin)

admin.site.register(Wishlist)

admin.site.register(Cart)

class CartItemAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(CartItem, CartItemAdmin)

admin.site.register(Wallet)

admin.site.register(WalletTransaction)

admin.site.register(Subscriber)