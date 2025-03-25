from django.utils import timezone

from decimal import Decimal

from products.models import Product
from promotions.models import Offer, Coupon


class OfferService:
    def __init__(self, product, variant_quantity, quantity, user=None, coupon_code=None):
        self.product = product
        self.variant_quantity = variant_quantity if variant_quantity is not None else 1
        self.quantity = quantity if quantity is not None else 1
        self.user = user
        self.coupon_code = coupon_code
        self.original_price = product.price if product else 0
        self.best_offer_discount = 0
        self.best_coupon_discount = 0


    def apply_offers(self):
        # Validate inputs before applying offers
        try:
            self.validate_inputs()
        except ValueError as e:
            print(f"Offer validation failed: {e}")
            return
    
        # Get current time for active offer validation
        current_time = timezone.now()

        # Fetch product and category-based offers
        product_offers = Offer.objects.filter(applicable_products=self.product, is_active=True, start_date__lte=current_time, end_date__gte=current_time)
        category_offers = Offer.objects.filter(applicable_categories=self.product.category, is_active=True, start_date__lte=current_time, end_date__gte=current_time)
        all_offers = product_offers.union(category_offers)
        
        # Calculate effective total amount
        effective_amount = self.variant_quantity * self.quantity * self.original_price
        
        # Calculate product discount if applicable
        product_discount = (effective_amount * self.product.discount / 100) if self.product.discount else 0
        
        # Track the best discount including product discount
        self.best_offer_discount = product_discount

        # Evaluate all offers to find the best
        for offer in all_offers:
            # Check minimum purchase value
            if offer.min_purchase_value and effective_amount < offer.min_purchase_value:
                continue

            # Calculate offer discount based on discount type
            if offer.discount_type == 'percentage':
                discount = max(min((effective_amount * offer.discount_value / 100), offer.max_discount_amount or float('inf')), 0)
            else:
                discount = min((offer.discount_value or 0), effective_amount)
            
            # Track the best offer including product discount
            self.best_offer_discount = max(self.best_offer_discount, discount)
            

    def apply_coupons(self):
        # Ensure coupon validation
        if self.coupon_code:
            try:
                self.validate_coupon()
            except ValueError as e:
                print(f"Coupon validation failed: {e}")
                return
            
            # Get the valid coupon object
            coupon = Coupon.objects.get(code=self.coupon_code)

            if coupon.apply_to_total_order:
                return
            
            # Calculate effective amount
            effective_amount = self.variant_quantity * self.quantity * self.product.price

            # Calculate the coupon discount
            if coupon.discount_type == 'percentage':
                self.best_coupon_discount = min((effective_amount * coupon.discount_value / 100), coupon.max_discount_amount or float('inf'))
            else:
                self.best_coupon_discount = min((coupon.discount_value or 0), effective_amount)


    def calculate_final_price(self):
        # Ensure only the best discount is applied
        offer_discount = self.best_offer_discount
        coupon_discount = self.best_coupon_discount
        # Determine the higher discount
        applied_discount = max(offer_discount, coupon_discount)
        
        # Calculate final price
        final_price = (self.variant_quantity * self.quantity * self.original_price) - applied_discount

        # Ensure final price is not negative
        return max(final_price, 0), applied_discount
    

    def validate_inputs(self):
        # Validate product
        if not self.product or not isinstance(self.product, Product):
            raise ValueError("Invalid product")
        if self.product.price <= 0:
            raise ValueError("Invalid product price")

        # Validate variant_quantity
        if not isinstance(self.variant_quantity, (int, float, Decimal)) or self.variant_quantity <= 0:
            raise ValueError("Invalid variant quantity")

        # Validate quantity
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("Invalid quantity")

        # Validate coupon if provided
        if self.coupon_code and not isinstance(self.coupon_code, str):
            raise ValueError("Invalid coupon code")


    def validate_coupon(self, cart_total=None):
        if not self.coupon_code:
            return  # No coupon to validate

        # Ensure coupon exists and is valid
        try:
            coupon = Coupon.objects.get(code=self.coupon_code)
        except Coupon.DoesNotExist:
            raise ValueError("The coupon code you entered is invalid.")
        
        # Validate coupon usage and expiration
        if not coupon.is_active:
            raise ValueError("The coupon is no longer active.")
        
        if not (coupon.start_date <= timezone.now() <= coupon.end_date):
            raise ValueError("This coupon is not valid at this time.")
        
        # Ensure user-specific coupon validation
        if coupon.users.exists() and not coupon.users.filter(id=self.user.id).exists():
            raise ValueError("This coupon is not valid for your account.")
        
        # Check minimum purchase requirement
        if cart_total is not None:
            if coupon.min_purchase_value and cart_total < coupon.min_purchase_value:
                raise ValueError("This coupon requires a minimum purchase of ₹{:.2f}.".format(coupon.min_purchase_value))
        else:
            effective_amount = self.variant_quantity * self.quantity * self.original_price
            if coupon.min_purchase_value and effective_amount < coupon.min_purchase_value:
                raise ValueError("This coupon requires a minimum purchase of ₹{:.2f}.".format(coupon.min_purchase_value))