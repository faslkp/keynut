from django import forms
from django.contrib.auth import get_user_model

from products.models import Product, Category
from .models import Offer, Coupon

User = get_user_model()

class OfferForm(forms.ModelForm):
    name = forms.CharField(
        label='Offer Name', 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Offer Name'}),
        required=True
    )
    offer_type = forms.ChoiceField(
        label='Offer Type', 
        choices=Offer.OFFER_TYPE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    discount_type = forms.ChoiceField(
        label='Discount Type', 
        choices=Offer.DISCOUNT_TYPE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    discount_value = forms.DecimalField(
        label='Discount Value', 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Discount Value'}),
        required=True
    )
    min_purchase_value = forms.DecimalField(
        label='Minimum Purchase Value', 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Minimum Purchase Value'}),
        required=False
    )
    max_discount_amount = forms.DecimalField(
        label='Maximum Discount Amount', 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Maximum Discount Amount'}),
        required=False
    )
    start_date = forms.DateTimeField(
        label='Start Date', 
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    end_date = forms.DateTimeField(
        label='End Date', 
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    applicable_products = forms.ModelMultipleChoiceField(
        label='Applicable Products',
        help_text='Hold down "Control", or "Command" on a Mac, to select more than one.',
        queryset=Product.objects.filter(is_deleted=False), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )
    applicable_categories = forms.ModelMultipleChoiceField(
        label='Applicable Categories', 
        help_text='Hold down "Control", or "Command" on a Mac, to select more than one.',
        queryset=Category.objects.filter(is_deleted=False), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = Offer
        exclude = ['is_active', 'applicable_categories', 'applicable_products']


class CouponForm(forms.ModelForm):
    code = forms.CharField(
        label='Coupon Code', 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Coupon Code'}),
        required=True
    )
    description = forms.CharField(
        label='Description', 
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter Description', 'rows': 3}),
        required=False
    )
    discount_type = forms.ChoiceField(
        label='Discount Type', 
        choices=Offer.DISCOUNT_TYPE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    discount_value = forms.DecimalField(
        label='Discount Value', 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Discount Value'}),
        required=True
    )
    min_purchase_value = forms.DecimalField(
        label='Minimum Purchase Value', 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Minimum Purchase Value'}),
        required=False
    )
    max_discount_amount = forms.DecimalField(
        label='Maximum Discount Amount', 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Maximum Discount Amount'}),
        required=False
    )
    apply_to_total_order = forms.BooleanField(
        label='Apply to Total Order', 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    single_use_per_user = forms.BooleanField(
        label='Single Use Per User', 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    start_date = forms.DateTimeField(
        label='Start Date', 
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    end_date = forms.DateTimeField(
        label='End Date', 
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    products = forms.ModelMultipleChoiceField(
        label='Products',
        help_text='Hold down "Control", or "Command" on a Mac, to select more than one.',
        queryset=Product.objects.filter(is_deleted=False), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )
    categories = forms.ModelMultipleChoiceField(
        label='Categories',
        help_text='Hold down "Control", or "Command" on a Mac, to select more than one.',
        queryset=Category.objects.filter(is_deleted=False), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )
    users = forms.ModelMultipleChoiceField(
        label='Users',
        help_text='Hold down "Control", or "Command" on a Mac, to select more than one.',
        queryset=User.objects.all(), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = Coupon
        exclude = ['is_active']