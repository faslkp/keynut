import base64
import json

from django.shortcuts import render, get_object_or_404
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError

from decimal import Decimal

from .models import Product, ProductVariant, Category
from .forms import ProductForm, CategoryForm


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
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
            for variant_id in selected_variants:
                variant = ProductVariant.objects.filter(id=variant_id).first()
                if variant:
                    product.variants.add(variant)

            return JsonResponse({
                "success": True,
                "message": f"Product {product.name} added successfully."
            })
        else:
            return JsonResponse({
                "error": True,
                "message": "Form validation failed!",
                "errors": form.errors
            })
    else:
        return JsonResponse({
            "error": True,
            "message": "Invalid request!"
        })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def edit_product(request, pk):
    if request.method == 'POST':
        try:
            product = Product.objects.filter(pk=pk).first()
            if not product:
                return JsonResponse({"error": True, "message": "Product not found!"}, status=404)
            form = ProductForm(request.POST, request.FILES, instance=product)
            if not form.is_valid():
                return JsonResponse({
                    "error": True,
                    "message": "Form validation failed!",
                    "errors": json.loads(form.errors.as_json())  # Returns detailed form errors
                })
            updated_product = form.save(commit=False)
            cropped_image_data = request.POST.get('cropped_image_data')
            try:
                if cropped_image_data:
                    # Decode the Base64 image
                    format, imgstr = cropped_image_data.split(';base64,')  
                    ext = format.split('/')[-1]  # Get file extension
                    
                    image_data = base64.b64decode(imgstr)
                    image_file = ContentFile(image_data, name=f"{updated_product.name}_cropped.{ext}")
                    
                    # Save the cropped image to the model
                    updated_product.image = image_file
            except Exception as e:
                return JsonResponse({"error": True, "message": f"Error processing image: {str(e)}"}, status=400)
            updated_product.save()
            # Handling variants safely
            selected_variants = request.POST.getlist('variants')

            try:
                selected_variant_ids = list(map(int, request.POST.getlist('variants')))  # Convert to integers

                # Get the corresponding ProductVariant objects
                selected_variants = ProductVariant.objects.filter(id__in=selected_variant_ids)

                # Update product variants (removes old ones and adds only selected ones)
                product.variants.set(selected_variants)

            except Exception as e:
                return JsonResponse({"error": True, "message": f"Error updating variants: {str(e)}"}, status=400)

            return JsonResponse({
                "success": True,
                "message": f"Product {updated_product.name} updated successfully."
            })

        except ValidationError as e:
            return JsonResponse({"error": True, "message": str(e)}, status=400)

        except Exception as e:
            return JsonResponse({
                "error": True,
                "message": "An unexpected error occurred!",
                "details": str(e)
            }, status=500)

    product = Product.objects.filter(pk=pk).first()
    variants = product.variants.all().values('id', 'quantity')
    if product:
        return JsonResponse({
            "success": True,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "discount": product.discount,
            "category": product.category.id,
            "unit": product.unit,
            "stock": product.stock,
            "image": product.image.url,
            "variants": list(variants),
        })
    else:
        return JsonResponse({
            "error": True,
            "message": "Product not found!"
        })


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
        new_stock = request.POST.get('new-stock')
        product = Product.objects.filter(pk=pk).first()
        if product:
            product.stock += Decimal(new_stock)
            product.save()
            return JsonResponse({
                "success": True,
                "message": f"Stock of {new_stock} {product.unit} added to {product.name}."
            })
        else:
            return JsonResponse({
                "error": True,
                "message": "Product not found!"
            })
    return JsonResponse({
        "error": True,
        "message": "Invalid request!"
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            category_name = form.cleaned_data['name']

            category, created = Category.objects.get_or_create(name=category_name)

            if created:
                return JsonResponse({
                    "success": True,
                    "message": f"Category {category.name} added successfully."
                })
            else:
                return JsonResponse({
                    "error": True,
                    "message": f"Category {category.name} already exists."
                })
    else:
        return JsonResponse({
            "error": True,
            "message": "Invalid request!"
        })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def edit_category(request, pk):
    if request.method == 'POST':
        category = Category.objects.filter(pk=pk).first()
        
        if category:
            form = CategoryForm(request.POST, instance=category)
            if form.is_valid():
                new_category_name = form.cleaned_data['name']

                # Check if there are other categories with the update name
                if Category.objects.filter(name=new_category_name).exclude(pk=pk).exists():
                    return JsonResponse({
                        "error": True,
                        "message": f"A category with name '{new_category_name}' already exists!"
                    })
                else:
                    form.save()

                    return JsonResponse({
                        "success": True,
                        "message": f"Category {category.name} updated successfully."
                    })
    return JsonResponse({
        "error": True,
        "message": "Invalid request!"
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='admin_login',redirect_field_name=None)
def delete_category(request, pk):
    if request.method == "POST":
        try:
            print("post received")
            category = Category.objects.filter(pk=pk).first()
            if category:
                print(category)
                category.is_deleted = not category.is_deleted
                category.save()

            return JsonResponse({
                "success" : True,
                "message" : f"Category {category.name} has {"deleted" if category.is_deleted else "restored"} successfully."
            })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)

