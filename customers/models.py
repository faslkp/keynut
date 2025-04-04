import random
import string

from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.conf import settings

from products.models import Product, ProductVariant
from promotions.services import OfferService
from promotions.models import Coupon


class Customer(AbstractUser):
    phone = models.CharField(max_length=15, null=True, blank=True)
    referral_key = models.CharField(max_length=10, blank=True)
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
        total_cart_value, total_items_level_discount = map(sum, zip(*(item.total_price() for item in self.cart_items.all())))
        
        # Apply cart-level coupon if applicable
        cart_level_discount = self.calculate_cart_level_coupon_discount(total_cart_value)
        final_cart_value = max(0, total_cart_value - cart_level_discount)
        
        total_discount = total_items_level_discount + cart_level_discount
        print('total dicount:', total_discount)
        print('cart level discount:', cart_level_discount)
        print('items level discount:', total_items_level_discount)
        print('cart value:', final_cart_value)
        return final_cart_value, total_discount, cart_level_discount
    

    def calculate_cart_level_coupon_discount(self, total_price):
        if not self.coupon or not self.coupon.apply_to_total_order:
            return 0

        offer_service = OfferService(
                None,
                None,
                None,
                user=self.user,
                coupon_code=self.coupon.code if self.coupon else None
            )
        try:
            offer_service.validate_coupon(cart_total=total_price)
        except ValueError as e:
            print(f"Coupon validation failed: {e}")
            return 0
        
        if self.coupon.discount_type == 'percentage':
            discount = (self.coupon.discount_value / 100) * total_price
            if self.coupon.max_discount_amount:
                discount = min(discount, self.coupon.max_discount_amount)
        else:
            discount = min(self.coupon.discount_value, total_price)
        
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
                user=self.cart.user,
                coupon_code=self.cart.coupon.code if self.cart.coupon else None
            )
            offer_service.apply_offers()
            offer_service.apply_coupons()
            
            # Calculate Final Price 
            final_price, disount = offer_service.calculate_final_price()
            
            return final_price, disount
        else:
            return 0, 0


    def __str__(self):
        return f"{self.quantity} x {self.variant.quantity}kg of {self.product.name} in {self.cart.user.username}'s cart"


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet of {self.user.username}"
    

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('add_money', 'Add Money'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('cashback', 'Cashback'),
        ('referral', 'Referral Bonus'),
    ]
    STATUS_TYPES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    transaction_id = models.UUIDField(unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, default='pending', choices=STATUS_TYPES)
    notes = models.CharField(max_length=255, null=True, blank=True)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.transaction_type} of {self.amount} in Wallet of {self.wallet.user.username}"
    

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class Message(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('pending', 'Pending'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField()
    acknowledge_number = models.CharField(max_length=20,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

    def __str__(self):
        return f"Query from {self.name} on {self.created_at}"

    def save(self, *args, **kwargs):
        if not self.acknowledgement_number:
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))  # 4-char alphanumeric
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding  # Checks if it's a new instance
        
        with transaction.atomic():
            super().save(*args, **kwargs)  # Save the object normally

            if is_new and not self.acknowledge_number:  # Generate ack number only for new orders
                id_part = f"{self.id:04d}"  # Ensures 4-digit enquiry ID
                random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))  # 4-char alphanumeric

                self.acknowledge_number = f"ACK-{id_part}-{random_str}"
                super().save(update_fields=['acknowledge_number'])  # Update only ack number