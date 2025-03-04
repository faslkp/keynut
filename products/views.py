import base64
import json

from django.shortcuts import render, get_object_or_404
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Product, ProductVariant
from .forms import ProductForm


def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid:
            product = form.save(commit=False)

            # Get the cropped image from hidden input (Base64 format)
            cropped_image_data = request.POST.get('cropped_image_data')

            if cropped_image_data:
                # Decode the Base64 image
                format, imgstr = cropped_image_data.split(';base64,')  
                ext = format.split('/')[-1]  # Get file extension
                
                image_data = base64.b64decode(imgstr)
                image_file = ContentFile(image_data, name=f"{product.name}_cropped.{ext}")
                
                # Save the cropped image to the model
                product.image = image_file

            product.save()  # Save product after updating image & thumbnail

            selected_variants = request.POST.getlist('variants')
            for variant in selected_variants:
                ProductVariant.objects.get_or_create(
                    product = product,
                    quantity = variant
                )

            return JsonResponse({
                "success": True,
                "message": f"Product {product.name} added successfully."
            })
    else:
        return JsonResponse({
            "error": True,
            "message": "Invalid request!"
        })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def edit_product(request):
    pass


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def unlist_product(request, pk):
    if request.method == "POST":
        try:
            product = get_object_or_404(Product, pk=pk)
            print(product.name)
            product.is_listed = not product.is_listed
            product.save()

            return JsonResponse({
                "success" : True,
                "message" : f"Customer {product.name} has {"listed" if product.is_listed else "unlisted"} successfully."
            })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def add_stock(request, pk):
    if request.method == 'POST':
        product = Product.objects.filter(pk=pk).first()
        if product:
            pass
        else:
            return JsonResponse({
                "error": True,
                "message": "Product not found!"
            })
    return JsonResponse({
        "error": True,
        "message": "Invalid request!"
    })