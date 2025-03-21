from django import template

from customers.models import Wishlist


register = template.Library()

@register.filter
def is_in_wishlist(product, user):
    if not user.is_authenticated:
        return False
    return Wishlist.objects.filter(user=user, product=product).exists()