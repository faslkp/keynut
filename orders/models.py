import random

from django.db import models
from django.contrib.auth import get_user_model

from products.models import Product

User = get_user_model()


class OrderAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=150)
    address_line_2 = models.CharField(max_length=150, null=True, blank=True)
    landmark = models.CharField(max_length=150, null=True, blank=True)
    pin = models.CharField(max_length=6)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}, {self.address_line_1}, {self.city}, {self.pin}"
    
    class Meta:
        verbose_name_plural = 'Order Addresses'


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Returned', 'Returned'),
        ('Refunded', 'Refunded'),
        ('Cancelled', 'Cancelled'),
    ]
    order_id = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders', related_query_name='order')
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.ForeignKey(OrderAddress, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Order ID: {self.order_id} - {self.status}"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding  # Checks if it's a new instance
        
        super().save(*args, **kwargs)  # Save the object normally

        if is_new and not self.order_id:  # Generate order_id only for new orders
            order_id_part = f"{self.id:06d}"  # Ensures 6-digit order ID
            random_part = f"{random.randint(100000, 999999)}"  # 6-digit random number

            self.order_id = f"ORD-{order_id_part}-{random_part}"
            super().save(update_fields=['order_id'])  # Update only order_id
    
    @property
    def total_amount(self):
        return sum(item.variant * item.quantity * item.price for item in self.order_items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='order_items', related_query_name='order_item')
    product = models.ForeignKey(Product, models.PROTECT)
    variant = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} in Order {self.order.id}"
    
    @property
    def total_amount(self):
        return self.variant * self.quantity * self.price


class Payment(models.Model):
    PAYMENT_CHOICES = [
        ('Pending', 'Pending'),
        ('Initiated', 'Initiated'),
        ('Processing', 'Processing'),
        ('Success', 'Success'),
        ('Failed', 'Failed')
    ]
    PAYMENT_METHODS = [
        ('cash-on-delivery', 'Cash on Delivery'),
        ('razorpay', 'RazorPay'),
        ('wallet', 'Wallet')
    ]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments', related_query_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='Pending')
    transaction_id = models.CharField(max_length=50, blank=True)
    payment_provider_order_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"₹{self.amount} | Order ID: {self.order.order_id} | Via: {self.payment_method}"