from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

from apps.core.models import (
    Topic, Category, SubCategory, Question,
    Answer, AnswerPoint, PDFUpload, Notification,
)
from apps.core.forms import (
    TopicForm, CategoryForm, SubCategoryForm,
    QuestionForm, AnswerForm, AnswerPointForm,
    PDFUploadForm, SearchForm,
)
from apps.core.services.question_service import create_question
from apps.core.services.search_service import global_search


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────

def home(request):
    recent_questions = Question.objects.select_related(
        "subcategory__category__topic", "created_by"
    ).order_by("-created_at")[:6]
    approved_topics = Topic.objects.filter(status="approved")[:8]
    context = {
        "recent_questions": recent_questions,
        "approved_topics": approved_topics,
    }
    return render(request, "home.html", context)


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────

def search_view(request):
    form = SearchForm(request.GET)
    results = {}
    query = ""
    if form.is_valid():
        query = form.cleaned_data.get("q", "")
        if query:
            results = global_search(query)
    return render(request, "search/search_results.html", {
        "form": form,
        "results": results,
        "query": query,
    })


# ─────────────────────────────────────────────
# TOPICS
# ─────────────────────────────────────────────

class TopicListView(ListView):
    model = Topic
    template_name = "topics/topic_list.html"
    context_object_name = "topics"
    paginate_by = 12

    def get_queryset(self):
        qs = Topic.objects.filter(status="approved").order_by("-created_at")
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class TopicDetailView(DetailView):
    model = Topic
    template_name = "topics/topic_detail.html"
    context_object_name = "topic"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = self.object.categories.filter(status="approved")
        return ctx


class TopicCreateView(LoginRequiredMixin, CreateView):
    model = Topic
    form_class = TopicForm
    template_name = "topics/topic_create.html"
    success_url = reverse_lazy("topic-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Topic submitted for approval.")
        return super().form_valid(form)


# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

class CategoryListView(ListView):
    model = Category
    template_name = "categories/category_list.html"
    context_object_name = "categories"
    paginate_by = 12

    def get_queryset(self):
        return Category.objects.filter(status="approved").select_related("topic").order_by("-created_at")


class CategoryDetailView(DetailView):
    model = Category
    template_name = "categories/category_detail.html"
    context_object_name = "category"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["subcategories"] = self.object.subcategories.filter(status="approved")
        return ctx


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "categories/category_create.html"
    success_url = reverse_lazy("category-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Category submitted for approval.")
        return super().form_valid(form)


# ─────────────────────────────────────────────
# SUBCATEGORIES
# ─────────────────────────────────────────────

class SubCategoryDetailView(DetailView):
    model = SubCategory
    template_name = "categories/subcategory_detail.html"
    context_object_name = "subcategory"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["questions"] = self.object.questions.select_related("created_by").order_by("-created_at")
        return ctx


class SubCategoryCreateView(LoginRequiredMixin, CreateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = "categories/subcategory_create.html"
    success_url = reverse_lazy("category-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Subcategory submitted for approval.")
        return super().form_valid(form)


# ─────────────────────────────────────────────
# QUESTIONS
# ─────────────────────────────────────────────

class QuestionListView(ListView):
    model = Question
    template_name = "questions/question_list.html"
    context_object_name = "questions"
    paginate_by = 15

    def get_queryset(self):
        qs = Question.objects.select_related(
            "subcategory__category__topic", "created_by"
        ).order_by("-created_at")
        q = self.request.GET.get("q", "")
        if q:
            qs = qs.filter(Q(title__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class QuestionDetailView(DetailView):
    model = Question
    template_name = "questions/question_detail.html"
    context_object_name = "question"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        Question.objects.filter(pk=obj.pk).update(view_count=obj.view_count + 1)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["answers"] = self.object.answers.prefetch_related("points").select_related("created_by")
        ctx["answer_form"] = AnswerForm()
        return ctx


@login_required
def question_create_view(request):
    form = QuestionForm(request.POST or None)
    duplicates = []
    if request.method == "POST" and form.is_valid():
        result = create_question(
            user=request.user,
            subcategory=form.cleaned_data["subcategory"],
            title=form.cleaned_data["title"],
        )
        if result["success"]:
            messages.success(request, "Question posted successfully.")
            return redirect("question-detail", pk=result["question"].pk)
        else:
            duplicates = result["duplicates"]
            messages.warning(request, "Similar questions already exist. Review them below.")
    return render(request, "questions/question_create.html", {
        "form": form,
        "duplicates": duplicates,
    })


# ─────────────────────────────────────────────
# ANSWERS
# ─────────────────────────────────────────────

@login_required
def answer_create_view(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    form = AnswerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        answer = form.save(commit=False)
        answer.question = question
        answer.created_by = request.user
        answer.save()
        messages.success(request, "Answer posted.")
        return redirect("question-detail", pk=question.pk)
    return render(request, "answers/answer_create.html", {
        "form": form,
        "question": question,
    })


@login_required
def answer_point_create_view(request, answer_pk):
    answer = get_object_or_404(Answer, pk=answer_pk)
    form = AnswerPointForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        point = form.save(commit=False)
        point.answer = answer
        point.created_by = request.user
        point.save()
        messages.success(request, "Point added.")
        return redirect("question-detail", pk=answer.question.pk)
    return render(request, "answers/answerpoint_create.html", {
        "form": form,
        "answer": answer,
    })


# ─────────────────────────────────────────────
# PDF UPLOAD
# ─────────────────────────────────────────────

@login_required
def pdf_upload_view(request):
    form = PDFUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        upload = form.save(commit=False)
        upload.uploaded_by = request.user
        upload.save()

        # Process synchronously for now (Celery can replace this later)
        from apps.core.services.pdf_processor import process_pdf
        process_pdf(str(upload.id))

        messages.success(request, "PDF uploaded and processed.")
        return redirect("upload-history")
    return render(request, "uploads/pdf_upload.html", {"form": form})

@login_required
def upload_history_view(request):
    uploads = PDFUpload.objects.filter(
        uploaded_by=request.user
    ).order_by("-created_at")
    return render(request, "uploads/upload_history.html", {"uploads": uploads})


# ─────────────────────────────────────────────
# USER DASHBOARD
# ─────────────────────────────────────────────

@login_required
def user_dashboard(request):
    user = request.user
    my_questions = Question.objects.filter(created_by=user).order_by("-created_at")[:5]
    my_answers = Answer.objects.filter(created_by=user).order_by("-created_at")[:5]
    my_uploads = PDFUpload.objects.filter(uploaded_by=user).order_by("-created_at")[:5]
    notifications = Notification.objects.filter(user=user, is_read=False).order_by("-created_at")[:10]
    return render(request, "dashboard/user_dashboard.html", {
        "my_questions": my_questions,
        "my_answers": my_answers,
        "my_uploads": my_uploads,
        "notifications": notifications,
    })


@login_required
def mark_notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER", "user-dashboard"))