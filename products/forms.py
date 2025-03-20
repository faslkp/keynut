from django import forms

from .models import Product, Category, ProductVariant


UNIT_CHOICES = [
    ('', 'Select a unit'),
    ('kg', 'Kilogram'),
    ('g', 'Gram'),
    ('pc', 'Piece'),
    ('l', 'Litre'),
    ('ml', 'Millilitre'),
    ('m', 'Meter'),
    ('cm', 'Centimeter'),
]


class ProductForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
        required=True
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter product description', 'rows': 3}),
        required=False
    )

    price = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price', 'step': '1.00'}),
        required=True
    )

    discount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter discount percentage', 'step': '1.00'}),
        required=True
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Category",
        required=True
    )

    unit = forms.ChoiceField(
        choices=UNIT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    stock = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
        required=True
    )

    variants = forms.ModelMultipleChoiceField(
        queryset=ProductVariant.objects.all().order_by('quantity'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )

    image = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'discount', 'category', 'unit', 'stock', 'image']
        
    def clean_image(self):
        image = self.cleaned_data.get("image")

        if not image:
            raise forms.ValidationError("Please upload a valid image.")

        return image  # Return the already cropped image
    

class CategoryForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
        required=True
    )

    class Meta:
        model = Category
        fields = ['name']