from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

# admin.site.register(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'is_blocked', 'is_deleted')}),
    )
    
