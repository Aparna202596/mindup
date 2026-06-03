from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, DetailView
from django.urls import reverse_lazy

from .models import Category, SubCategory
from .forms import CategoryForm, SubCategoryForm


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "categories/category_create.html"
    success_url = reverse_lazy("category-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class CategoryListView(ListView):
    model = Category
    template_name = "categories/category_list.html"
    context_object_name = "categories"
    paginate_by = 10

    def get_queryset(self):
        return Category.objects.filter(status="approved")


class CategoryDetailView(DetailView):
    model = Category
    template_name = "categories/category_detail.html"


class SubCategoryCreateView(LoginRequiredMixin, CreateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = "categories/subcategory_create.html"
    success_url = reverse_lazy("subcategory-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class SubCategoryListView(ListView):
    model = SubCategory
    template_name = "categories/subcategory_list.html"
    context_object_name = "subcategories"
    paginate_by = 10

    def get_queryset(self):
        return SubCategory.objects.filter(status="approved")


class SubCategoryDetailView(DetailView):
    model = SubCategory
    template_name = "categories/subcategory_detail.html"
