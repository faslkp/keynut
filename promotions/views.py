import json

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test

from promotions.forms import OfferForm, CouponForm
from promotions.models import Coupon, Offer
from orders.models import Order

@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def add_offer(request):
    """Add offer from Admin Panel."""
    if request.method == 'POST':
        form = OfferForm(request.POST, request.FILES)
        if form.is_valid():
            offer = form.save()

            # Get multiple selected values correctly
            offer.applicable_products.set(request.POST.getlist("applicable_products"))
            offer.applicable_categories.set(request.POST.getlist("applicable_categories"))

            return JsonResponse({
                'success': True,
                'message': f"Offer {offer.name} added successfully.",
            })
        else:
            return JsonResponse({
                'error': True,
                'message': f"{form.errors}",
            })
    return JsonResponse({
        'error': True,
        'message': 'Invalid request.',
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def edit_offer(request, pk):
    """Edit offer from Admin Panel.
    
    POST request update the record.
    GET request fetch the rocord.
    """
    offer = Offer.objects.filter(pk=pk).first()

    if not offer:
        return JsonResponse({
            'error': True,
            'message': "Offer not found!"
        })
    
    if request.method == 'POST':
        form = OfferForm(request.POST, request.FILES, instance=offer)
        if form.is_valid():
            edited_instance = form.save()

            # Get multiple selected values correctly
            offer.applicable_products.set(request.POST.getlist("applicable_products"))
            offer.applicable_categories.set(request.POST.getlist("applicable_categories"))
            
            return JsonResponse({
                'success': True,
                'message': f"{edited_instance.name} offer details updated successfully."
            })
    
    form = OfferForm(instance=offer)

    # Prepare JSON response
    data = form.initial  # Get basic form field values
    
    # Convert ManyToMany fields into lists of IDs
    data["applicable_products"] = list(offer.applicable_products.values_list("id", flat=True))
    data["applicable_categories"] = list(offer.applicable_categories.values_list("id", flat=True))


    # Replace image field with its URL
    if offer.banner_image:  
        data["banner_image"] = offer.banner_image.url  
    else:
        data["banner_image"] = None
    
    return JsonResponse({
        'success': True,
        'message': 'Coupon details fetched successfully.',
        'data': data,
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def disable_offer(request, pk):
    """Disable or enable offer from Admin Panel."""
    if request.method == "POST":
        try:
            offer = Offer.objects.filter(pk=pk).first()
            if offer:
                offer.is_active = not offer.is_active
                offer.save()

                return JsonResponse({
                    "success" : True,
                    "message" : f"Offer {offer.name} has updated successfully."
                })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def remove_offer(request, pk):
    """Delete offer from Admin Panel.
    
    Item will be removed from the database.
    """
    if request.method == "POST":
        try:
            offer = Offer.objects.filter(pk=pk).first()
            if offer:
                offer.delete()

                return JsonResponse({
                    "success" : True,
                    "message" : f"Offer {offer.name} has deleted successfully."
                })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def add_coupon(request):
    """Add coupon from Admin Panel."""
    if request.method == 'POST':
        # Check if coupon already exists
        coupon_code = request.POST.get('code')
        if Coupon.objects.filter(code=coupon_code).exists():
            return JsonResponse({
                'error': True,
                'message': f"Coupon {coupon_code} already exists.",
            })
        
        # Create a copy of POST data for the form
        post_data = request.POST.copy()

        form = CouponForm(post_data)
        if form.is_valid():
            coupon = form.save()

            # Get multiple selected values correctly
            coupon.products.set(request.POST.getlist("products"))
            coupon.categories.set(request.POST.getlist("categories"))
            coupon.users.set(request.POST.getlist("users"))

            return JsonResponse({
                'success': True,
                'message': f"Offer {coupon.code} added successfully.",
            })
        else:
            return JsonResponse({
                'error': True,
                'message': "Invalid or incomplete data received. Please correct and resubmit",
            })
        
    return JsonResponse({
        'error': True,
        'message': 'Invalid request.',
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def edit_coupon(request, pk):
    """Edit coupon from Admin Panel.
    
    POST request update the record.
    GET request fetch the record.
    """
    coupon = Coupon.objects.filter(pk=pk).first()

    if not coupon:
        return JsonResponse({
            'error': True,
            'message': "Coupon not found!"
        })
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            edited_instance = form.save()
            
            return JsonResponse({
                'success': True,
                'message': f"{edited_instance.code} coupon details updated successfully."
            })
    
    form = CouponForm(instance=coupon)

    # Prepare JSON response
    data = form.initial  # Get basic form field values

    # Convert ManyToMany fields into lists of IDs
    data["users"] = list(coupon.users.values_list("id", flat=True))
    data["products"] = list(coupon.products.values_list("id", flat=True))
    data["categories"] = list(coupon.categories.values_list("id", flat=True))
    
    return JsonResponse({
        'success': True,
        'message': 'Coupon details fetched successfully.',
        'data': data,
    })


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def disable_coupon(request, pk):
    """Disable coupon from Admin Panel."""
    if request.method == "POST":
        try:
            coupon = Coupon.objects.filter(pk=pk).first()
            if coupon:
                coupon.is_active = not coupon.is_active
                coupon.save()

                return JsonResponse({
                    "success" : True,
                    "message" : f"Coupon {coupon.code} has updated successfully."
                })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)


@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def remove_coupon(request, pk):
    """Delete coupon from Admin Panel. 
    
    Item will be removed from the database.
    """
    if request.method == "POST":
        try:
            coupon = Coupon.objects.filter(pk=pk).first()
            if coupon:
                if Order.objects.filter(coupon=coupon).exists():
                    return JsonResponse({
                        "error" : True,
                        "message" : f"Coupon {coupon.code} cannot be deleted as there are orders linked to this coupon."
                    })

                else:
                    coupon.delete()

                    return JsonResponse({
                        "success" : True,
                        "message" : f"Coupon {coupon.code} has deleted successfully."
                    })
        except json.JSONDecodeError:
            return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)
        
    return JsonResponse({"error" : True, "message" : "Invalid request!"}, status=400)

