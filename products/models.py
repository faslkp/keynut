import os
import uuid

from django.db import models
from django.db.models import Avg, Count
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.apps import apps
from django.conf import settings

from decimal import Decimal
from PIL import Image
from io import BytesIO


class Category(models.Model):
    name = models.CharField(max_length=20)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name)
            while Category.objects.filter(slug=slug).exists():
                slug = f"{slug}-{uuid.uuid4().hex[:6]}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"


class ProductVariant(models.Model):
    quantity = models.DecimalField(max_digits=10, decimal_places=2, unique=True)

    def __str__(self):
        return f"{self.quantity}"
    
    def get_display_quantity(self, unit):
        unit_conversion = {
            'kg': ('g', 1000),
            'm': ('cm', 100),
            'l': ('ml', 1000),
        }
        
        if unit in unit_conversion and self.quantity < 1:
            smaller_unit, factor = unit_conversion[unit]
            converted_quantity = self.quantity * factor
            return f"{converted_quantity.quantize(Decimal('1')) if converted_quantity == converted_quantity.to_integral() else converted_quantity.normalize()} {smaller_unit}"


        return f"{self.quantity.quantize(Decimal('1')) if self.quantity == self.quantity.to_integral() else self.quantity.normalize()} {unit}"



class Product(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', related_query_name='product')
    image = models.ImageField(upload_to='products/cropped/')
    # Stored thumbnail (auto generated when saving)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True, null=True)
    unit = models.CharField(max_length=15)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    variants = models.ManyToManyField(ProductVariant)
    relevance = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    @property
    def discount_price(self):
        return self.price - (self.price * (self.discount/100))
    
    @property
    def is_in_stock(self):
        lowest_variant = self.variants.order_by('quantity').first()
        return True if lowest_variant and self.stock >= lowest_variant.quantity else False
    
    def is_in_wishlist(self, user):
        if not user.is_authenticated:
            return False
        Wishlist = apps.get_model('customers', 'Wishlist')
        return Wishlist.objects.filter(user=user, product=self).exists()
    
    def update_rating(self):
        """Recalculate and update the average rating."""
        rating_data = self.ratings.aggregate(avg_rating=Avg('rating'), count=Count('rating'))
        self.average_rating = rating_data['avg_rating'] or 0
        self.rating_count = rating_data['count']
        self.save()

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name)
            while Product.objects.filter(slug=slug).exists():
                slug = f"{slug}-{uuid.uuid4().hex[:6]}"
            self.slug = slug

        # Check if this is an existing object and if image changed
        is_new = not self.pk
        image_changed = False
        
        if not is_new:
            try:
                original = Product.objects.get(pk=self.pk)
                # Compare image fields - handle cases where image might be None
                image_changed = (bool(original.image) != bool(self.image) or 
                            (original.image and self.image and original.image.name != self.image.name))
            except Product.DoesNotExist:
                is_new = True  # Treat as new if original not found

        # First save to ensure we have a pk and image is saved
        super().save(*args, **kwargs)

        # Generate thumbnail if:
        # 1. There's an image AND
        # 2. Either it's new with no thumbnail OR image changed OR thumbnail missing
        if self.image and (is_new or image_changed or not self.thumbnail):
            try:
                img = Image.open(self.image.path)  # Use .path to ensure we get the saved file

                # Convert RGBA to RGB if needed
                if img.mode == "RGBA":
                    img = img.convert("RGB")

                # Resize to thumbnail size
                img.thumbnail((300, 300))

                # Save the thumbnail to memory
                thumb_io = BytesIO()
                img.save(thumb_io, format='JPEG', quality=100)
                thumb_filename = f"thumb_{os.path.basename(self.image.name)}"
                thumb_file = ContentFile(thumb_io.getvalue(), name=thumb_filename)

                # Assign and save thumbnail
                self.thumbnail = thumb_file
                super().save(update_fields=['thumbnail'])
            except Exception as e:
                print(f"Error generating thumbnail: {str(e)}")
        else:
            print("No thumbnail generation needed")

    def __str__(self):
        return self.name

class Rating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')

    def save(self, *args, **kwargs):
        """Save the rating and update product's average rating."""
        super().save(*args, **kwargs)
        self.product.update_rating()
    
    def delete(self, *args, **kwargs):
        """Delete rating and update product's average rating."""
        super().delete(*args, **kwargs)
        self.product.update_rating()

    def __str__(self):
        return f"Rating of {self.user.first_name} on {self.product.name}"

