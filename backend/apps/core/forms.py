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

WIDGET = {"class": "form-control"}
SELECT = {"class": "form-select"}


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={**WIDGET, "placeholder": "Topic name"}),
            "description": forms.Textarea(attrs={**WIDGET, "rows": 3}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        validate_no_special_only(name)
        return name


class TopicEditForm(forms.ModelForm):
    """Admin edit — can change status too."""
    class Meta:
        model = Topic
        fields = ["name", "description", "status"]
        widgets = {
            "name": forms.TextInput(attrs=WIDGET),
            "description": forms.Textarea(attrs={**WIDGET, "rows": 3}),
            "status": forms.Select(attrs=SELECT),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["topic", "name", "description"]
        widgets = {
            "topic": forms.Select(attrs=SELECT),
            "name": forms.TextInput(attrs={**WIDGET, "placeholder": "Category name"}),
            "description": forms.Textarea(attrs={**WIDGET, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topic"].queryset = Topic.objects.filter(status="approved")


class CategoryEditForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["topic", "name", "description", "status"]
        widgets = {
            "topic": forms.Select(attrs=SELECT),
            "name": forms.TextInput(attrs=WIDGET),
            "description": forms.Textarea(attrs={**WIDGET, "rows": 3}),
            "status": forms.Select(attrs=SELECT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topic"].queryset = Topic.objects.all()


class SubCategoryForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ["category", "name"]
        widgets = {
            "category": forms.Select(attrs=SELECT),
            "name": forms.TextInput(attrs={**WIDGET, "placeholder": "Subcategory name"}),
        }

    def __init__(self, *args, **kwargs):
        # Accept optional category_pk to pre-select
        category_pk = kwargs.pop("category_pk", None)
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(status="approved")
        if category_pk:
            self.fields["category"].initial = category_pk


class SubCategoryEditForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ["category", "name", "status"]
        widgets = {
            "category": forms.Select(attrs=SELECT),
            "name": forms.TextInput(attrs=WIDGET),
            "status": forms.Select(attrs=SELECT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["subcategory", "title"]
        widgets = {
            "subcategory": forms.Select(attrs=SELECT),
            "title": forms.Textarea(attrs={**WIDGET, "rows": 3, "placeholder": "Ask your question..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subcategory"].queryset = SubCategory.objects.filter(
            status="approved"
        ).select_related("category__topic")

    def clean_title(self):
        title = self.cleaned_data["title"]
        validate_question_length(title)
        return title


class QuestionEditForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["subcategory", "title"]
        widgets = {
            "subcategory": forms.Select(attrs=SELECT),
            "title": forms.Textarea(attrs={**WIDGET, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subcategory"].queryset = SubCategory.objects.all().select_related("category__topic")


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={**WIDGET, "rows": 5, "placeholder": "Write your answer..."}),
        }

    def clean_content(self):
        content = self.cleaned_data["content"]
        validate_answer_length(content)
        return content


class AnswerEditForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={**WIDGET, "rows": 5}),
        }


class AnswerPointForm(forms.ModelForm):
    class Meta:
        model = AnswerPoint
        fields = ["point"]
        widgets = {
            "point": forms.Textarea(attrs={**WIDGET, "rows": 2, "placeholder": "Add a key point..."}),
        }


class BulkQAUploadForm(forms.Form):
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.filter(status="approved").order_by("name"),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_topic"}),
        label="Topic",
        empty_label="— Select Topic —",
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),   # populated via AJAX
        widget=forms.Select(attrs={"class": "form-select", "id": "id_category",
                                   "disabled": "disabled"}),
        label="Category",
        empty_label="— Select Category —",
    )
    subcategory = forms.ModelChoiceField(
        queryset=SubCategory.objects.none(),  # populated via AJAX
        widget=forms.Select(attrs={"class": "form-select", "id": "id_subcategory",
                                   "disabled": "disabled"}),
        label="Subcategory",
        empty_label="— Select Subcategory —",
    )
    raw_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control font-monospace",
            "rows": 20,
            "placeholder": (
                "Paste your Q&A content here. Supported formats:\n\n"
                "Format 1 — Q: / A: markers:\n"
                "Q: What is Python?\n"
                "A: Python is a high-level programming language.\n\n"
                "Format 2 — Numbered questions:\n"
                "1. What is Django?\n"
                "Django is a Python web framework.\n\n"
                "Format 3 — Heading blocks:\n"
                "Q1. What is REST?\n"
                "Answer: REST stands for Representational State Transfer."
            ),
            "spellcheck": "false",
        }),
        label="Paste Q&A Content",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On POST, re-populate category/subcategory querysets for validation
        if args and args[0]:
            topic_id = args[0].get("topic")
            category_id = args[0].get("category")
            if topic_id:
                self.fields["category"].queryset = Category.objects.filter(
                    topic_id=topic_id, status="approved"
                )
                self.fields["category"].widget.attrs.pop("disabled", None)
            if category_id:
                self.fields["subcategory"].queryset = SubCategory.objects.filter(
                    category_id=category_id, status="approved"
                )
                self.fields["subcategory"].widget.attrs.pop("disabled", None)

    def clean_raw_text(self):
        text = self.cleaned_data.get("raw_text", "").strip()
        if len(text) < 20:
            raise forms.ValidationError("Please paste at least some Q&A content.")
        return text


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


class ManualQuestionAnswerForm(forms.Form):
    """For manually adding Q&A without duplicate detection."""
    subcategory = forms.ModelChoiceField(
        queryset=SubCategory.objects.filter(status="approved"),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Subcategory",
    )
    title = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3,
                                     "placeholder": "Question text..."}),
        label="Question",
    )
    answer_content = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5,
                                     "placeholder": "Answer text..."}),
        label="Answer",
        required=False,
    )

    def clean_title(self):
        title = self.cleaned_data["title"]
        validate_question_length(title)
        return title