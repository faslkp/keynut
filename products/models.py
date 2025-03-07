import random
import os

from django.db import models
from django.utils.text import slugify
from django.core.files.base import ContentFile

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
                slug = f"{slug}-{random.randint(1000,9999)}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
    

class Product(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', related_query_name='variant')
    image = models.ImageField(upload_to='products/cropped/')
    # Stored thumbnail (auto generated when saving)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True, null=True)
    unit = models.CharField(max_length=15)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    relevance = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_listed = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name)
            while Product.objects.filter(slug=slug).exists():
                slug = f"{slug}-{random.randint(1000, 9999)}"
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


VARIANT_CHOICES = [
    (0.1, "0.1 unit"),
    (0.2, "0.2 unit"),
    (0.25, "0.25 unit"),
    (0.5, "0.5 unit"),
    (0.75, "0.75 unit"),
    (1, "1 unit"),
    (1.5, "1.5 unit"),
    (2, "2 unit"),
    (3, "3 unit"),
    (5, "5 unit"),
]


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', related_query_name='variant')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, choices=VARIANT_CHOICES)

    def __str__(self):
        return f"{self.quantity} {self.product.unit} of {self.product.name}"

