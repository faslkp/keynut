from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from promotions.forms import OfferForm, CouponForm
from promotions.models import Coupon

@login_required(login_url='admin_login')
@user_passes_test(lambda user : user.is_staff, login_url='unavailable',redirect_field_name=None)
def add_offer(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save()
            return JsonResponse({
                'success': True,
                'message': f"Offer {offer.name} added successfully.",
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
def add_coupon(request):
    if request.method == 'POST':
        
        # Check if coupon already exists
        coupon_code = request.POST.get('code')
        if Coupon.objects.filter(code=coupon_code).exists():
            return JsonResponse({
                'error': True,
                'message': f"Coupon {coupon_code} already exists.",
            })
        
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save()
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

