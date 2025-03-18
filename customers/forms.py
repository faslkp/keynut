from django import forms
from django.contrib.auth import get_user_model

from . models import Address

User = get_user_model()


class CustomerForm(forms.ModelForm):
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
        required=True
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        required=True
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class AddressForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name (Required)*'}),
        required=True
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number (Required)*'}),
        required=True
    )
    address_line_1 = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House No., Building Name, Street (Required)*'}),
        required=True
    )
    address_line_2 = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area, Locality'}),
        required=False
    )
    landmark = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nearby Famous Shop/Mall/Landmark'}),
        required=False
    )
    pin = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode (Required)*'}),
        required=True
    )
    city = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City (Required)*'}),
        required=True
    )
    state = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State (Required)*'}),
        required=True
    )

    class Meta:
        model = Address
        fields = ['name', 'phone', 'address_line_1', 'address_line_2', 'landmark', 'pin', 'city', 'state']