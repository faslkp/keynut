from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

# admin.site.register(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:  # If editing an existing user
            fieldsets += (("Password", {"fields": ("password",)}),)
        return fieldsets
    pass
