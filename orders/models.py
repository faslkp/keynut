import random

from django.db import models
from django.contrib.auth import get_user_model

from products.models import Product
from promotions.models import Coupon

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
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('return_requested', 'Return Requested'),
        ('return_approved', 'Return Approved'),
        ('return_rejected', 'Return Rejected'),
        ('return_received', 'Return Recieved'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    order_id = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders', related_query_name='order')
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.ForeignKey(OrderAddress, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    order_level_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, null=True, blank=True)

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
    
    @property
    def total_discount(self):
        return sum(item.discount_amount for item in self.order_items.all())
    
    def get_next_statuses(self):
        """Returns only the allowed next statuses dynamically"""
        order_statuses = [choice for choice, value in self.STATUS_CHOICES]
        if self.status in order_statuses:
            current_index = order_statuses.index(self.status)
            print(order_statuses[current_index+1:5])
            return order_statuses[current_index + 1:6]
        return []


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='order_items', related_query_name='order_item')
    product = models.ForeignKey(Product, models.PROTECT)
    variant = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.product.name} in Order {self.order.order_id}"
    
    @property
    def total_amount(self):
        return self.variant * self.quantity * self.price


class Payment(models.Model):
    PAYMENT_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('wallet_topup', 'Wallet Top-Up'),
        ('adjustment', 'Adjustment'),
    ]
    PAYMENT_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ]
    PAYMENT_METHODS = [
        ('cash-on-delivery', 'Cash on Delivery'),
        ('razorpay', 'RazorPay'),
        ('wallet', 'Wallet')
    ]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True, related_name='payments', related_query_name='payment')
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='payments', related_query_name='payment')
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=50, blank=True)
    payment_provider_order_id = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"₹{self.amount} | Order ID: {self.order.order_id} | Via: {self.payment_method} | {self.payment_status}"


class ReturnRequest(models.Model):
    RETURN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved'),
        ('received', 'Received'),
        ('refunded', 'Refunded'),
    ]
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name='returns', related_query_name='return')
    reason = models.TextField()
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_next_statuses(self):
        """Returns only the allowed next statuses dynamically"""
        statuses = [choice for choice, value in self.RETURN_STATUS_CHOICES]
        if self.status in statuses:
            current_index = statuses.index(self.status)
            return statuses[current_index + 1:4]
        return []

    def __str__(self):
        return f"Return for {self.order_item.product.name} {self.order_item.variant} {self.order_item.product.unit} (Qty:{self.order_item.quantity}) in order {self.order_item.order.order_id} - Status: {self.status}"
