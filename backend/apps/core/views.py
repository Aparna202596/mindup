from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.utils import timezone

from apps.core.models import (
    Topic, Category, SubCategory, Question,
    Answer, AnswerPoint, PDFUpload, Notification, AuditLog,
)
from apps.core.forms import (
    TopicForm, TopicEditForm,
    CategoryForm, CategoryEditForm,
    SubCategoryForm, SubCategoryEditForm,
    QuestionForm, QuestionEditForm,
    AnswerForm, AnswerEditForm,
    AnswerPointForm,
    PDFUploadForm, SearchForm,
    ManualQuestionAnswerForm,
)
from apps.core.services.question_service import create_question
from apps.core.services.search_service import global_search
from apps.core.services.audit_service import create_audit_log
from apps.core.permissions import admin_required


# ── HOME ──────────────────────────────────────────────────────────────────────

def home(request):
    recent_questions = Question.objects.select_related(
        "subcategory__category__topic", "created_by"
    ).order_by("-created_at")[:6]
    approved_topics = Topic.objects.filter(status="approved").annotate(
        cat_count=Count("categories")
    )[:8]
    return render(request, "home.html", {
        "recent_questions": recent_questions,
        "approved_topics":  approved_topics,
        "total_questions":  Question.objects.count(),
        "total_answers":    Answer.objects.count(),
    })


def smart_login_redirect(request):
    if request.user.is_authenticated and getattr(request.user, "is_admin", False):
        return redirect("admin-dashboard")
    return redirect("home")


# ── SEARCH ────────────────────────────────────────────────────────────────────

def search_view(request):
    form = SearchForm(request.GET)
    results, query = {}, ""
    if form.is_valid():
        query = form.cleaned_data.get("q", "")
        if query:
            results = global_search(query)
    return render(request, "search/search_results.html", {
        "form": form, "results": results, "query": query,
    })


# ── TOPICS ────────────────────────────────────────────────────────────────────

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


@admin_required
def topic_edit(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    form = TopicEditForm(request.POST or None, instance=topic)
    if request.method == "POST" and form.is_valid():
        old = {"name": topic.name, "status": topic.status}
        form.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Topic",
                         object_id=topic.id, old_data=old,
                         new_data={"name": topic.name, "status": topic.status})
        messages.success(request, "Topic updated.")
        return redirect("admin-content")
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Topic", "object": topic,
        "cancel_url": "admin-content",
    })


@admin_required
def topic_delete(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="Topic",
                         object_id=topic.id, old_data={"name": topic.name})
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect("admin-content")
    return render(request, "confirm_delete.html", {"object": topic, "type": "Topic",
                                                    "cancel_url": "admin-content"})


# ── CATEGORIES ────────────────────────────────────────────────────────────────

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


@admin_required
def category_edit(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    form = CategoryEditForm(request.POST or None, instance=cat)
    if request.method == "POST" and form.is_valid():
        old = {"name": cat.name, "status": cat.status}
        form.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Category",
                         object_id=cat.id, old_data=old,
                         new_data={"name": cat.name, "status": cat.status})
        messages.success(request, "Category updated.")
        return redirect("admin-content")
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Category", "object": cat,
        "cancel_url": "admin-content",
    })


@admin_required
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="Category",
                         object_id=cat.id, old_data={"name": cat.name})
        cat.delete()
        messages.success(request, "Category deleted.")
        return redirect("admin-content")
    return render(request, "confirm_delete.html", {"object": cat, "type": "Category",
                                                    "cancel_url": "admin-content"})


# ── SUBCATEGORIES ─────────────────────────────────────────────────────────────

class SubCategoryDetailView(DetailView):
    model = SubCategory
    template_name = "categories/subcategory_detail.html"
    context_object_name = "subcategory"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["questions"] = self.object.questions.select_related("created_by").order_by("-created_at")
        return ctx


@login_required
def subcategory_create(request, category_pk=None):
    """
    Works two ways:
      /subcategories/create/                 → blank form
      /categories/<pk>/add-subcategory/      → pre-selects the category
    """
    category = None
    if category_pk:
        category = get_object_or_404(Category, pk=category_pk, status="approved")

    form = SubCategoryForm(request.POST or None,
                           category_pk=str(category.pk) if category else None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, "Subcategory submitted for approval.")
        if category:
            return redirect("category-detail", pk=category.pk)
        return redirect("category-list")

    return render(request, "categories/subcategory_create.html", {
        "form": form,
        "preselected_category": category,
    })


@admin_required
def subcategory_edit(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    form = SubCategoryEditForm(request.POST or None, instance=sub)
    if request.method == "POST" and form.is_valid():
        old = {"name": sub.name, "status": sub.status}
        form.save()
        create_audit_log(user=request.user, action="EDIT", object_type="SubCategory",
                         object_id=sub.id, old_data=old,
                         new_data={"name": sub.name, "status": sub.status})
        messages.success(request, "Subcategory updated.")
        return redirect("admin-content")
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Subcategory", "object": sub,
        "cancel_url": "admin-content",
    })


@admin_required
def subcategory_delete(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="SubCategory",
                         object_id=sub.id, old_data={"name": sub.name})
        sub.delete()
        messages.success(request, "Subcategory deleted.")
        return redirect("admin-content")
    return render(request, "confirm_delete.html", {"object": sub, "type": "Subcategory",
                                                    "cancel_url": "admin-content"})


# ── QUESTIONS ─────────────────────────────────────────────────────────────────

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
            create_audit_log(user=request.user, action="CREATE", object_type="Question",
                             object_id=result["question"].id,
                             new_data={"title": result["question"].title})
            messages.success(request, "Question posted successfully.")
            return redirect("question-detail", pk=result["question"].pk)
        else:
            duplicates = result["duplicates"]
            messages.warning(request, "Similar questions exist. Review them before posting.")
    return render(request, "questions/question_create.html", {
        "form": form, "duplicates": duplicates,
    })


@login_required
def manual_qa_create(request):
    """Add a question + answer together, skipping duplicate detection."""
    form = ManualQuestionAnswerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        from apps.core.services.duplicate_detector import normalize_question
        title = form.cleaned_data["title"]
        subcategory = form.cleaned_data["subcategory"]
        answer_content = form.cleaned_data.get("answer_content", "").strip()

        question = Question.objects.create(
            subcategory=subcategory,
            title=title,
            normalized_title=normalize_question(title),
            created_by=request.user,
        )
        create_audit_log(user=request.user, action="CREATE", object_type="Question",
                         object_id=question.id, new_data={"title": title})

        if answer_content:
            Answer.objects.create(
                question=question,
                content=answer_content,
                created_by=request.user,
            )

        messages.success(request, "Question and answer saved successfully.")
        return redirect("question-detail", pk=question.pk)

    return render(request, "questions/manual_qa_create.html", {"form": form})


@admin_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk)
    form = QuestionEditForm(request.POST or None, instance=question)
    if request.method == "POST" and form.is_valid():
        old = {"title": question.title}
        from apps.core.services.duplicate_detector import normalize_question
        question = form.save(commit=False)
        question.normalized_title = normalize_question(question.title)
        question.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Question",
                         object_id=question.id, old_data=old,
                         new_data={"title": question.title})
        messages.success(request, "Question updated.")
        return redirect("question-detail", pk=question.pk)
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Question", "object": question,
        "cancel_url": None,
        "cancel_href": f"/questions/{question.pk}/",
    })


@admin_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="Question",
                         object_id=question.id, old_data={"title": question.title})
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect("question-list")
    return render(request, "confirm_delete.html", {
        "object": question, "type": "Question",
        "cancel_href": f"/questions/{question.pk}/",
    })


# ── ANSWERS ───────────────────────────────────────────────────────────────────

@login_required
def answer_create_view(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    form = AnswerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        answer = form.save(commit=False)
        answer.question   = question
        answer.created_by = request.user
        answer.save()
        create_audit_log(user=request.user, action="CREATE", object_type="Answer",
                         object_id=answer.id, new_data={"question": str(question.id)})
        messages.success(request, "Answer posted.")
        return redirect("question-detail", pk=question.pk)
    return render(request, "answers/answer_create.html", {"form": form, "question": question})


@admin_required
def answer_edit(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    form = AnswerEditForm(request.POST or None, instance=answer)
    if request.method == "POST" and form.is_valid():
        old = {"content": answer.content}
        form.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Answer",
                         object_id=answer.id, old_data=old,
                         new_data={"content": answer.content[:100]})
        messages.success(request, "Answer updated.")
        return redirect("question-detail", pk=answer.question.pk)
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Answer", "object": answer,
        "cancel_href": f"/questions/{answer.question.pk}/",
    })


@admin_required
def answer_delete(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    question_pk = answer.question.pk
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="Answer",
                         object_id=answer.id)
        answer.delete()
        messages.success(request, "Answer deleted.")
        return redirect("question-detail", pk=question_pk)
    return render(request, "confirm_delete.html", {
        "object": answer, "type": "Answer",
        "cancel_href": f"/questions/{question_pk}/",
    })


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
    return render(request, "answers/answerpoint_create.html", {"form": form, "answer": answer})


# ── PDF UPLOAD ────────────────────────────────────────────────────────────────

@login_required
def pdf_upload_view(request):
    form = PDFUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        upload = form.save(commit=False)
        upload.uploaded_by = request.user
        upload.save()
        from apps.core.services.pdf_processor import process_pdf
        report = process_pdf(str(upload.id))
        q_count = report.get("questions_created", 0)
        messages.success(request,
            f"PDF processed: {q_count} question(s) extracted. "
            f"Check upload history for the full report.")
        return redirect("upload-history")
    return render(request, "uploads/pdf_upload.html", {"form": form})


@login_required
def upload_history_view(request):
    uploads = PDFUpload.objects.filter(uploaded_by=request.user).order_by("-created_at")
    return render(request, "uploads/upload_history.html", {"uploads": uploads})


# ── USER DASHBOARD ────────────────────────────────────────────────────────────

@login_required
def user_dashboard(request):
    user = request.user
    notification_qs = Notification.objects.filter(user=user)
    return render(request, "dashboard/user_dashboard.html", {
        "my_questions":  Question.objects.filter(created_by=user).order_by("-created_at")[:5],
        "my_answers":    Answer.objects.filter(created_by=user).select_related("question").order_by("-created_at")[:5],
        "my_uploads":    PDFUpload.objects.filter(uploaded_by=user).order_by("-created_at")[:5],
        "my_topics":     Topic.objects.filter(created_by=user).order_by("-created_at")[:5],
        "notifications": notification_qs.order_by("-created_at")[:10],
        "unread_count":  notification_qs.filter(is_read=False).count(),
    })


@login_required
def mark_notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER", "/dashboard/"))


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("user-dashboard")


# ── AUDIT LOG ─────────────────────────────────────────────────────────────────

@admin_required
def audit_log_view(request):
    logs = AuditLog.objects.select_related("user").order_by("-created_at")
    action_filter = request.GET.get("action", "")
    type_filter   = request.GET.get("type", "")
    if action_filter:
        logs = logs.filter(action=action_filter)
    if type_filter:
        logs = logs.filter(object_type=type_filter)
    page = Paginator(logs, 30).get_page(request.GET.get("page", 1))
    return render(request, "dashboard/audit_log.html", {
        "page": page,
        "action_filter": action_filter,
        "type_filter":   type_filter,
        "actions": AuditLog.objects.values_list("action", flat=True).distinct(),
        "types":   AuditLog.objects.values_list("object_type", flat=True).distinct(),
    })


# ── CONTENT MANAGEMENT (admin) ────────────────────────────────────────────────

@admin_required
def admin_content_view(request):
    """Single page showing all content with edit/delete controls."""
    tab = request.GET.get("tab", "topics")
    context = {
        "tab": tab,
        "tab_list": [
            ("topics", "Topics"),
            ("categories", "Categories"),
            ("subcategories", "Subcategories"),
            ("questions", "Questions"),
            ("answers", "Answers"),
        ],
    }

    if tab == "topics":
        context["items"] = Topic.objects.order_by("-created_at")
    elif tab == "categories":
        context["items"] = Category.objects.select_related("topic").order_by("-created_at")
    elif tab == "subcategories":
        context["items"] = SubCategory.objects.select_related("category__topic").order_by("-created_at")
    elif tab == "questions":
        context["items"] = Question.objects.select_related(
            "subcategory__category__topic", "created_by"
        ).order_by("-created_at")
    elif tab == "answers":
        context["items"] = Answer.objects.select_related(
            "question", "created_by"
        ).order_by("-created_at")

    return render(request, "dashboard/admin_content.html", context)


# ── USER MANAGEMENT ───────────────────────────────────────────────────────────

@admin_required
def user_list_view(request):
    from apps.core.models import CustomUser, Role
    return render(request, "dashboard/user_list.html", {
        "users": CustomUser.objects.select_related("role").order_by("-date_joined"),
        "roles": Role.objects.all(),
    })


@admin_required
def user_role_update(request, pk):
    from apps.core.models import CustomUser, Role
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == "POST":
        role_id = request.POST.get("role_id")
        if role_id:
            user.role = get_object_or_404(Role, pk=role_id)
            user.save()
            messages.success(request, f"Role updated for {user.email}.")
    return redirect("user-list")