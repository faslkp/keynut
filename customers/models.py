from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

from products.models import Product, ProductVariant
from promotions.services import OfferService
from promotions.models import Coupon


class Customer(AbstractUser):
    phone = models.CharField(max_length=15, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=150)
    address_line_2 = models.CharField(max_length=150, null=True, blank=True)
    landmark = models.CharField(max_length=150, null=True, blank=True)
    pin = models.CharField(max_length=6)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}, {self.address_line_1}, {self.city}, {self.pin}"
    
    class Meta:
        verbose_name_plural = 'Addresses'


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} in Wishlist of {self.user.first_name} {self.user.last_name}"


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def total_price(self):
        total_order_price, total_items_discount = map(sum, zip(*(item.total_price() for item in self.cart_items.all())))
        
        # Apply cart-level coupon if applicable
        total_cart_level_discount = self.calculate_total_coupon_discount(total_order_price)
        total_order_price -= total_cart_level_discount
        
        total_discount = total_items_discount + total_cart_level_discount

        return total_order_price, total_discount, total_cart_level_discount
    

    def calculate_total_coupon_discount(self, total_price):
        if not self.coupon or not self.coupon.apply_to_total_order:
            return 0

        if self.coupon.discount_type == 'percentage':
            discount = (self.coupon.discount_value / 100) * total_price
            if self.coupon.max_discount_amount:
                discount = min(discount, self.coupon.max_discount_amount)
        else:
            discount = self.coupon.discount_value
        
        return discount


    def shipping_charge(self):
        cart_total = self.total_price()[0]  # Get total price without discount
        return 40 if cart_total < 1000 else 0


    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)  # Number of packets
    added_at = models.DateTimeField(auto_now_add=True)


    def total_price(self):
        # Check if the total required quantity is within stock and then calculate total price
        if self.variant.quantity * self.quantity <= self.product.stock:
            offer_service = OfferService(
                self.product, 
                self.variant.quantity, 
                self.quantity, 
                coupon_code=self.cart.coupon.code if self.cart.coupon else None
            )
            offer_service.apply_offers()
            offer_service.apply_coupons()
            
            # Calculate Final Price
            discounted_price, disount = offer_service.calculate_final_price()
            final_price = discounted_price * self.variant.quantity * self.quantity
            
            return final_price, disount
        else:
            return 0, 0


    def __str__(self):
        return f"{self.quantity} x {self.variant.quantity}kg of {self.product.name} in {self.cart.user.username}'s cart"
