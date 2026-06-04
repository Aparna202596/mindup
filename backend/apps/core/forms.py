from django import forms
from apps.core.models import (
    Topic, Category, SubCategory, Question,
    Answer, AnswerPoint, PDFUpload,
)
from apps.core.validators import (
    validate_no_special_only,
    validate_question_length,
    validate_answer_length,
    validate_pdf_extension,
)


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Topic name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Brief description"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        validate_no_special_only(name)
        return name


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["topic", "name", "description"]
        widgets = {
            "topic": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topic"].queryset = Topic.objects.filter(status="approved")


class SubCategoryForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ["category", "name"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Subcategory name"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(status="approved")


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["subcategory", "title"]
        widgets = {
            "subcategory": forms.Select(attrs={"class": "form-select"}),
            "title": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Ask your question..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subcategory"].queryset = SubCategory.objects.filter(status="approved")

    def clean_title(self):
        title = self.cleaned_data["title"]
        validate_question_length(title)
        return title


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Write your answer..."}),
        }

    def clean_content(self):
        content = self.cleaned_data["content"]
        validate_answer_length(content)
        return content


class AnswerPointForm(forms.ModelForm):
    class Meta:
        model = AnswerPoint
        fields = ["point"]
        widgets = {
            "point": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Add a key point..."}),
        }


class PDFUploadForm(forms.ModelForm):
    class Meta:
        model = PDFUpload
        fields = ["file"]
        widgets = {
            "file": forms.FileInput(attrs={"class": "form-control", "accept": ".pdf"}),
        }

    def clean_file(self):
        f = self.cleaned_data["file"]
        validate_pdf_extension(f)
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File size must be under 10 MB.")
        return f


class SearchForm(forms.Form):
    q = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Search questions, topics...",
            "autocomplete": "off",
        })
    )