from django import forms

from apps.categories.models import Category, SubCategory

class CategoryForm(forms.ModelForm):

    class Meta:

        model = Category

        fields = [
            "topic",
            "name",
            "description"
        ]

class SubCategoryForm(forms.ModelForm):

    class Meta:

        model = SubCategory

        fields = [
            "category",
            "name"
        ]