from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.core.models import (
    Topic, Category, SubCategory, Question,
    Answer, AnswerPoint, PDFUpload, Notification, AuditLog,
)
from apps.core.forms import (
    TopicForm, CategoryForm, SubCategoryForm,
    QuestionForm, AnswerForm, AnswerPointForm,
    PDFUploadForm, SearchForm,
)
from apps.core.services.question_service import create_question
from apps.core.services.search_service import global_search
from apps.core.services.audit_service import create_audit_log
from apps.core.permissions import admin_required, AdminRequiredMixin


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────

def home(request):
    recent_questions = Question.objects.select_related(
        "subcategory__category__topic", "created_by"
    ).order_by("-created_at")[:6]
    approved_topics = Topic.objects.filter(status="approved").annotate(
        cat_count=Count("categories")
    )[:8]
    total_questions = Question.objects.count()
    total_answers   = Answer.objects.count()
    return render(request, "home.html", {
        "recent_questions": recent_questions,
        "approved_topics":  approved_topics,
        "total_questions":  total_questions,
        "total_answers":    total_answers,
    })


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────

def search_view(request):
    form  = SearchForm(request.GET)
    results = {}
    query = ""
    if form.is_valid():
        query = form.cleaned_data.get("q", "")
        if query:
            results = global_search(query)
    return render(request, "search/search_results.html", {
        "form": form, "results": results, "query": query,
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
        response = super().form_valid(form)
        messages.success(self.request, "Topic submitted for approval.")
        return response


@admin_required
def topic_delete(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    if request.method == "POST":
        create_audit_log(
            user=request.user, action="DELETE", object_type="Topic",
            object_id=topic.id, old_data={"name": topic.name},
        )
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect("topic-list")
    return render(request, "confirm_delete.html", {"object": topic, "type": "Topic"})


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
        response = super().form_valid(form)
        messages.success(self.request, "Category submitted for approval.")
        return response


@admin_required
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        create_audit_log(
            user=request.user, action="DELETE", object_type="Category",
            object_id=cat.id, old_data={"name": cat.name},
        )
        cat.delete()
        messages.success(request, "Category deleted.")
        return redirect("category-list")
    return render(request, "confirm_delete.html", {"object": cat, "type": "Category"})


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
        response = super().form_valid(form)
        messages.success(self.request, "Subcategory submitted for approval.")
        return response


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
        ctx["answers"]     = self.object.answers.prefetch_related("points").select_related("created_by")
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
            create_audit_log(
                user=request.user, action="CREATE", object_type="Question",
                object_id=result["question"].id,
                new_data={"title": result["question"].title},
            )
            messages.success(request, "Question posted successfully.")
            return redirect("question-detail", pk=result["question"].pk)
        else:
            duplicates = result["duplicates"]
            messages.warning(request, "Similar questions exist. Review them before posting.")
    return render(request, "questions/question_create.html", {
        "form": form, "duplicates": duplicates,
    })


@admin_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == "POST":
        create_audit_log(
            user=request.user, action="DELETE", object_type="Question",
            object_id=question.id, old_data={"title": question.title},
        )
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect("question-list")
    return render(request, "confirm_delete.html", {"object": question, "type": "Question"})


# ─────────────────────────────────────────────
# ANSWERS
# ─────────────────────────────────────────────

@login_required
def answer_create_view(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    form = AnswerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        answer = form.save(commit=False)
        answer.question   = question
        answer.created_by = request.user
        answer.save()
        create_audit_log(
            user=request.user, action="CREATE", object_type="Answer",
            object_id=answer.id, new_data={"question": str(question.id)},
        )
        messages.success(request, "Answer posted.")
        return redirect("question-detail", pk=question.pk)
    return render(request, "answers/answer_create.html", {
        "form": form, "question": question,
    })


@admin_required
def answer_delete(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    question_pk = answer.question.pk
    if request.method == "POST":
        create_audit_log(
            user=request.user, action="DELETE", object_type="Answer",
            object_id=answer.id,
        )
        answer.delete()
        messages.success(request, "Answer deleted.")
        return redirect("question-detail", pk=question_pk)
    return render(request, "confirm_delete.html", {"object": answer, "type": "Answer"})


@login_required
def answer_point_create_view(request, answer_pk):
    answer = get_object_or_404(Answer, pk=answer_pk)
    form = AnswerPointForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        point = form.save(commit=False)
        point.answer     = answer
        point.created_by = request.user
        point.save()
        messages.success(request, "Key point added.")
        return redirect("question-detail", pk=answer.question.pk)
    return render(request, "answers/answerpoint_create.html", {
        "form": form, "answer": answer,
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
        from apps.core.services.pdf_processor import process_pdf
        process_pdf(str(upload.id))
        messages.success(request, "PDF uploaded and processed successfully.")
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
    my_answers = Answer.objects.filter(created_by=user).select_related("question").order_by("-created_at")[:5]
    my_uploads = PDFUpload.objects.filter(uploaded_by=user).order_by("-created_at")[:5]
    my_topics = Topic.objects.filter(created_by=user).order_by("-created_at")[:5]
    notification_qs = Notification.objects.filter(user=user)
    unread_count = notification_qs.filter(is_read=False).count()
    notifications = notification_qs.order_by("-created_at")[:10]
    
    return render(request, "dashboard/user_dashboard.html", {
        "my_questions":  my_questions,
        "my_answers":    my_answers,
        "my_uploads":    my_uploads,
        "my_topics":     my_topics,
        "notifications": notifications,
        "unread_count":  unread_count,
    })


@login_required
def mark_notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER", "user-dashboard"))


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("user-dashboard")


# ─────────────────────────────────────────────
# AUDIT LOG (admin only)
# ─────────────────────────────────────────────

@admin_required
def audit_log_view(request):
    logs = AuditLog.objects.select_related("user").order_by("-created_at")
    action_filter = request.GET.get("action", "")
    type_filter   = request.GET.get("type", "")
    if action_filter:
        logs = logs.filter(action=action_filter)
    if type_filter:
        logs = logs.filter(object_type=type_filter)

    from django.core.paginator import Paginator
    paginator = Paginator(logs, 30)
    page      = paginator.get_page(request.GET.get("page", 1))

    actions = AuditLog.objects.values_list("action", flat=True).distinct()
    types   = AuditLog.objects.values_list("object_type", flat=True).distinct()

    return render(request, "dashboard/audit_log.html", {
        "page":          page,
        "action_filter": action_filter,
        "type_filter":   type_filter,
        "actions":       actions,
        "types":         types,
    })


# ─────────────────────────────────────────────
# USER MANAGEMENT (admin only)
# ─────────────────────────────────────────────

@admin_required
def user_list_view(request):
    from apps.core.models import CustomUser, Role
    users = CustomUser.objects.select_related("role").order_by("-date_joined")
    roles = Role.objects.all()
    return render(request, "dashboard/user_list.html", {
        "users": users, "roles": roles,
    })


@admin_required
def user_role_update(request, pk):
    from apps.core.models import CustomUser, Role
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == "POST":
        role_id = request.POST.get("role_id")
        if role_id:
            role = get_object_or_404(Role, pk=role_id)
            user.role = role
            user.save()
            messages.success(request, f"Role updated for {user.email}.")
        return redirect("user-list")
    return redirect("user-list")

@login_required
def smart_login_redirect(request):
    if getattr(request.user, "is_admin", False):
        return redirect("admin-dashboard")
    return redirect("home")