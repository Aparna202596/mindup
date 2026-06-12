import re
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
    Answer, AnswerPoint, PDFUpload, Notification, AuditLog, ApprovalQueue,
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
from apps.core.services.duplicate_detector import is_duplicate_answer
from core.decorators import admin_login_required, user_login_required
from django.views.decorators.cache import never_cache
from allauth.account import views as allauth_views

from apps.core.forms import BulkQAUploadForm
from apps.core.models import BulkUploadSession
from apps.core.services.bulk_qa_parser import process_bulk_upload

# ── HOME ──────────────────────────────────────────────────────────────────────
@never_cache
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


@never_cache
def smart_login_redirect(request):
    if request.user.is_authenticated and getattr(request.user, "is_admin", False):
        return redirect("admin-dashboard")
    return redirect("home")


# ── SEARCH ────────────────────────────────────────────────────────────────────
@never_cache
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
@admin_login_required
@user_login_required
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

@admin_login_required
@user_login_required
class TopicDetailView(DetailView):
    model = Topic
    template_name = "topics/topic_detail.html"
    context_object_name = "topic"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = self.object.categories.filter(status="approved")
        return ctx

@admin_login_required
@user_login_required
class TopicCreateView(LoginRequiredMixin, CreateView):
    model = Topic
    form_class = TopicForm
    template_name = "topics/topic_create.html"
    success_url = reverse_lazy("topic-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Topic submitted for approval.")
        return super().form_valid(form)


@admin_login_required
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
        return redirect("admin-dashboard")
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Topic", "object": topic,
        "cancel_url": "admin-dashboard",
    })


@admin_login_required
def topic_delete(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="Topic",
                         object_id=topic.id, old_data={"name": topic.name})
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect("admin-dashboard")
    return render(request, "confirm_delete.html", {
        "object": topic, "type": "Topic", "cancel_url": "admin-dashboard",
    })


# ── CATEGORIES ────────────────────────────────────────────────────────────────
@admin_login_required
@user_login_required
class CategoryListView(ListView):
    model = Category
    template_name = "categories/category_list.html"
    context_object_name = "categories"
    paginate_by = 12

    def get_queryset(self):
        return Category.objects.filter(status="approved").select_related("topic").order_by("-created_at")

@admin_login_required
@user_login_required
class CategoryDetailView(DetailView):
    model = Category
    template_name = "categories/category_detail.html"
    context_object_name = "category"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["subcategories"] = self.object.subcategories.filter(status="approved")
        return ctx

@admin_login_required
@user_login_required
class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "categories/category_create.html"
    success_url = reverse_lazy("category-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Category submitted for approval.")
        return super().form_valid(form)


@admin_login_required
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
        return redirect("admin-dashboard")
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Category", "object": cat,
        "cancel_url": "admin-dashboard",
    })


@admin_login_required
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="Category",
                         object_id=cat.id, old_data={"name": cat.name})
        cat.delete()
        messages.success(request, "Category deleted.")
        return redirect("admin-dashboard")
    return render(request, "confirm_delete.html", {
        "object": cat, "type": "Category", "cancel_url": "admin-dashboard",
    })


# ── SUBCATEGORIES ─────────────────────────────────────────────────────────────
@admin_login_required
@user_login_required
class SubCategoryDetailView(DetailView):
    model = SubCategory
    template_name = "categories/subcategory_detail.html"
    context_object_name = "subcategory"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["questions"] = self.object.questions.select_related("created_by").order_by("-created_at")
        return ctx


@admin_login_required
@user_login_required
def subcategory_create(request, category_pk=None):
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


@admin_login_required
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
        return redirect("admin-dashboard")
    return render(request, "dashboard/edit_form.html", {
        "form": form, "title": "Edit Subcategory", "object": sub,
        "cancel_url": "admin-dashboard",
    })


@admin_login_required
def subcategory_delete(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    if request.method == "POST":
        create_audit_log(user=request.user, action="DELETE", object_type="SubCategory",
                         object_id=sub.id, old_data={"name": sub.name})
        sub.delete()
        messages.success(request, "Subcategory deleted.")
        return redirect("admin-dashboard")
    return render(request, "confirm_delete.html", {
        "object": sub, "type": "Subcategory", "cancel_url": "admin-dashboard",
    })


# ── QUESTIONS ─────────────────────────────────────────────────────────────────
@admin_login_required
@user_login_required
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

@admin_login_required
@user_login_required
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
        ctx["point_form"]  = AnswerPointForm()
        return ctx

@admin_login_required
@user_login_required
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



@admin_login_required
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
        "cancel_href": f"/questions/{question.pk}/",
    })


@admin_login_required
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

@admin_login_required
@user_login_required
def answer_create_view(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    form = AnswerForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        content = form.cleaned_data["content"]

        # Duplicate answer check
        if is_duplicate_answer(content, question_pk):
            messages.warning(request, "A very similar answer already exists for this question.")
            return render(request, "answers/answer_create.html", {"form": form, "question": question})

        answer = form.save(commit=False)
        answer.question   = question
        answer.created_by = request.user
        answer.save()

        create_audit_log(user=request.user, action="CREATE", object_type="Answer",
                         object_id=answer.id, new_data={"question": str(question.id)})
        messages.success(request, "Answer posted.")
        return redirect("question-detail", pk=question.pk)

    return render(request, "answers/answer_create.html", {"form": form, "question": question})


@admin_login_required
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


@admin_login_required
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


@admin_login_required
@user_login_required
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

@user_login_required('core.bulk_upload_question')
def bulk_qa_upload(request):


    form = BulkQAUploadForm(request.POST or None)
    report = None

    if request.method == "POST" and form.is_valid():
        subcategory = form.cleaned_data["subcategory"]
        raw_text    = form.cleaned_data["raw_text"]

        # Create session record
        session = BulkUploadSession.objects.create(
            uploaded_by=request.user,
            topic=form.cleaned_data["topic"],
            category=form.cleaned_data["category"],
            subcategory=subcategory,
            raw_text=raw_text,
        )

        report = process_bulk_upload(
            user=request.user,
            subcategory=subcategory,
            raw_text=raw_text,
            session=session,
        )

        if report["questions_created"] > 0:
            messages.success(
                request,
                f"✓ {report['questions_created']} question(s) and "
                f"{report['answers_created']} answer(s) saved successfully."
            )
        if report["duplicates_skipped"]:
            messages.warning(
                request,
                f"⚠ {len(report['duplicates_skipped'])} duplicate(s) skipped."
            )
        if report.get("errors"):
            messages.error(request, f"✗ {len(report['errors'])} error(s) during processing.")

        # Don't redirect — show report on same page
        form = BulkQAUploadForm()  # reset form after success

    # AJAX: return categories for a topic
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return _ajax_load_options(request)

    return render(request, "questions/bulk_qa_upload.html", {
        "form":   form,
        "report": report,
    })


def ajax_load_categories(request):
    """AJAX: return <option> list for a given topic_id."""
    topic_id = request.GET.get("topic_id")
    cats = Category.objects.filter(
        topic_id=topic_id, status="approved"
    ).order_by("name").values("id", "name")
    data = [{"id": str(c["id"]), "name": c["name"]} for c in cats]
    from django.http import JsonResponse
    return JsonResponse({"categories": data})


def ajax_load_subcategories(request):
    """AJAX: return <option> list for a given category_id."""
    cat_id = request.GET.get("category_id")
    subs = SubCategory.objects.filter(
        category_id=cat_id, status="approved"
    ).order_by("name").values("id", "name")
    data = [{"id": str(s["id"]), "name": s["name"]} for s in subs]
    from django.http import JsonResponse
    return JsonResponse({"subcategories": data})


# 7. Update user_dashboard — remove PDF references:
@user_login_required()
@never_cache
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect("admin-dashboard")
    user = request.user
    notification_qs = Notification.objects.filter(user=user)
    return render(request, "dashboard/user_dashboard.html", {
        "my_questions":     Question.objects.filter(created_by=user).order_by("-created_at")[:5],
        "my_answers":       Answer.objects.filter(created_by=user).select_related("question").order_by("-created_at")[:5],
        "my_bulk_uploads":  BulkUploadSession.objects.filter(uploaded_by=user).order_by("-created_at")[:5],
        "my_topics":        Topic.objects.filter(created_by=user).order_by("-created_at")[:5],
        "notifications":    notification_qs.order_by("-created_at")[:10],
        "unread_count":     notification_qs.filter(is_read=False).count(),
    })

@admin_login_required
@user_login_required
def mark_notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER", "/dashboard/"))


@admin_login_required
@user_login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("user-dashboard")


# ── AUDIT LOG ─────────────────────────────────────────────────────────────────

@admin_login_required
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


# ── CONTENT MANAGEMENT (admin) — kept as alias for admin-dashboard tab ────────

@admin_login_required
def admin_content_view(request):
    """Redirect to admin dashboard with the correct tab."""
    tab = request.GET.get("tab", "topics")
    return redirect(f"/admin-dashboard/?tab={tab}")


# ── USER MANAGEMENT ───────────────────────────────────────────────────────────

@admin_login_required
def user_list_view(request):
    from apps.core.models import CustomUser, Role
    return render(request, "dashboard/user_list.html", {
        "users": CustomUser.objects.select_related("role").order_by("-date_joined"),
        "roles": Role.objects.all(),
    })


@admin_login_required
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
