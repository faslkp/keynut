from django.contrib import admin

from . models import Product, ProductVariant, Category


admin.site.register(Product)
admin.site.register(ProductVariant)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']
    fields = ['name']

admin.site.register(Category, CategoryAdmin)

