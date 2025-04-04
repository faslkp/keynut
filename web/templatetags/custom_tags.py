from django import template

from customers.models import Wishlist


register = template.Library()

@register.filter
def is_in_wishlist(product, user):
    if not user.is_authenticated:
        return False
    return Wishlist.objects.filter(user=user, product=product).exists()


@register.filter
def get_index(value, index):
    try:
        return value[index]
    except (IndexError, TypeError):
        return None


@register.filter
def get_item(dictionary, key):
    """Returns dictionary value for a given key"""
    return dictionary.get(key, key)  # Default to key if not found



