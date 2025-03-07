from django import forms

from .models import Product, Category, VARIANT_CHOICES


class ProductForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
        required=True
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter product description', 'rows': 3}),
        required=True
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

    unit = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unit (e.g., kg, pcs)'}),
        required=True
    )

    stock = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
        required=True
    )

    variants = forms.MultipleChoiceField(
        choices=VARIANT_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
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