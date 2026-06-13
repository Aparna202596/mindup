import json
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.core.decorators import (
    admin_login_required,
    user_login_required,
    UserLoginRequiredMixin,
)
from apps.core.models import (
    Topic, Category, SubCategory, Question,
    Answer, AnswerPoint, BulkUploadSession,
    Notification, AuditLog, ApprovalQueue, Favorite,
)
from apps.core.forms import (
    TopicForm, TopicEditForm,
    CategoryForm, CategoryEditForm,
    SubCategoryForm, SubCategoryEditForm,
    QuestionForm, QuestionEditForm,
    AnswerForm, AnswerEditForm,
    AnswerPointForm,
    BulkQAUploadForm, SearchForm,
)
from apps.core.services.question_service import create_question
from apps.core.services.search_service import global_search
from apps.core.services.audit_service import create_audit_log
from apps.core.services.duplicate_detector import is_duplicate_answer
from apps.core.services.bulk_qa_parser import process_bulk_upload

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _json_ok(data=None, **kwargs):
    payload = {"success": True}
    if data:
        payload.update(data)
    payload.update(kwargs)
    return JsonResponse(payload)


def _json_err(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _user_favorite_ids(user, content_type):
    if not user.is_authenticated:
        return set()
    return set(
        Favorite.objects.filter(user=user, content_type=content_type)
        .values_list("object_id", flat=True)
    )


# ══════════════════════════════════════════════════════════════════════════════
# HOME & AUTH REDIRECT
# ══════════════════════════════════════════════════════════════════════════════

@never_cache
def home(request):
    """Landing page → redirect to login if not authenticated."""
    if not request.user.is_authenticated:
        return redirect("account_login")
    if request.user.is_superuser:
        return redirect("admin-dashboard")
    return redirect("user-dashboard")


@never_cache
def smart_login_redirect(request):
    if request.user.is_authenticated:
        if getattr(request.user, "is_admin", False):
            return redirect("admin-dashboard")
        return redirect("user-dashboard")
    return redirect("account_login")


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════════

@never_cache
def search_view(request):
    form           = SearchForm(request.GET)
    results, query = {}, ""
    if form.is_valid():
        query = form.cleaned_data.get("q", "")
        if query:
            results = global_search(query)
    return render(request, "search_results.html", {
        "form": form, "results": results, "query": query,
    })


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — Dynamic selects
# ══════════════════════════════════════════════════════════════════════════════

def ajax_load_categories(request):
    topic_id = request.GET.get("topic_id", "")
    cats = (
        Category.objects
        .filter(topic_id=topic_id, status="approved")
        .order_by("name")
        .values("id", "name")
    )
    return JsonResponse({"categories": [
        {"id": str(c["id"]), "name": c["name"]} for c in cats
    ]})


def ajax_load_subcategories(request):
    cat_id = request.GET.get("category_id", "")
    subs = (
        SubCategory.objects
        .filter(category_id=cat_id, status="approved")
        .order_by("name")
        .values("id", "name")
    )
    return JsonResponse({"subcategories": [
        {"id": str(s["id"]), "name": s["name"]} for s in subs
    ]})


# ══════════════════════════════════════════════════════════════════════════════
# FAVORITES (AJAX)
# ══════════════════════════════════════════════════════════════════════════════

@user_login_required()
def toggle_favorite(request):
    if request.method != "POST":
        return _json_err("POST required", 405)
    try:
        body         = json.loads(request.body)
        content_type = body.get("content_type")
        object_id    = body.get("object_id")
    except Exception:
        return _json_err("Invalid JSON")

    VALID_TYPES = {"topic", "category", "subcategory", "question"}
    if content_type not in VALID_TYPES:
        return _json_err("Invalid content_type")

    fav, created = Favorite.objects.get_or_create(
        user=request.user,
        content_type=content_type,
        object_id=object_id,
    )
    if not created:
        fav.delete()
        return _json_ok(favorited=False, message="Removed from favorites")
    return _json_ok(favorited=True, message="Added to favorites")


@user_login_required()
@never_cache
def favorites_page(request):
    user = request.user
    favs = Favorite.objects.filter(user=user)

    fav_topic_ids  = set(favs.filter(content_type="topic").values_list("object_id", flat=True))
    fav_cat_ids    = set(favs.filter(content_type="category").values_list("object_id", flat=True))
    fav_subcat_ids = set(favs.filter(content_type="subcategory").values_list("object_id", flat=True))
    fav_q_ids      = set(favs.filter(content_type="question").values_list("object_id", flat=True))

    return render(request, "favorites.html", {
        "fav_topics":        Topic.objects.filter(id__in=fav_topic_ids),
        "fav_categories":    Category.objects.filter(id__in=fav_cat_ids).select_related("topic"),
        "fav_subcategories": SubCategory.objects.filter(id__in=fav_subcat_ids).select_related("category__topic"),
        "fav_questions":     Question.objects.filter(id__in=fav_q_ids).select_related("subcategory__category__topic"),
    })


# ══════════════════════════════════════════════════════════════════════════════
# TOPICS — AJAX CRUD + hide/unhide/delete
# ══════════════════════════════════════════════════════════════════════════════

@user_login_required()
@never_cache
def topic_list_view(request):
    is_admin = request.user.is_superuser
    q = request.GET.get("q", "")

    if is_admin:
        qs = Topic.objects.annotate(
            q_count=Count("categories__subcategories__questions", distinct=True)
        ).order_by("-created_at")
    else:
        qs = Topic.objects.filter(
            status="approved", is_hidden=False
        ).annotate(
            q_count=Count("categories__subcategories__questions", distinct=True)
        ).filter(q_count__gt=0).order_by("name")

    if q:
        qs = qs.filter(name__icontains=q)

    paginator = Paginator(qs, 12)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    fav_ids = _user_favorite_ids(request.user, "topic")

    return render(request, "topic_list.html", {
        "topics":       page_obj,
        "page_obj":     page_obj,
        "search_query": q,
        "is_admin":     is_admin,
        "fav_ids":      fav_ids,
    })


@user_login_required()
@never_cache
def topic_detail_view(request, pk):
    topic    = get_object_or_404(Topic, pk=pk)
    is_admin = request.user.is_superuser

    if not is_admin:
        if topic.status != "approved" or topic.is_hidden:
            from django.http import Http404
            raise Http404

    if is_admin:
        categories = topic.categories.prefetch_related(
            "subcategories__questions__answers"
        ).order_by("name")
    else:
        categories = topic.categories.filter(
            status="approved", is_hidden=False
        ).prefetch_related(
            "subcategories__questions__answers"
        ).order_by("name")

    fav_topic_ids  = _user_favorite_ids(request.user, "topic")
    fav_cat_ids    = _user_favorite_ids(request.user, "category")
    fav_subcat_ids = _user_favorite_ids(request.user, "subcategory")
    fav_q_ids      = _user_favorite_ids(request.user, "question")

    return render(request, "detail_unified.html", {
        "topic":         topic,
        "categories":    categories,
        "is_admin":      is_admin,
        "fav_topic_ids":  fav_topic_ids,
        "fav_cat_ids":   fav_cat_ids,
        "fav_subcat_ids": fav_subcat_ids,
        "fav_q_ids":     fav_q_ids,
    })


@admin_login_required
def topic_create_ajax(request):
    if request.method != "POST":
        return _json_err("POST required", 405)
    form = TopicForm(request.POST)
    if form.is_valid():
        topic            = form.save(commit=False)
        topic.created_by = request.user
        topic.status     = "approved"   # admin creates = auto-approved
        topic.save()
        create_audit_log(user=request.user, action="CREATE", object_type="Topic",
                         object_id=topic.id, new_data={"name": topic.name})
        return _json_ok(id=str(topic.id), name=topic.name, message="Topic created.")
    return _json_err(str(form.errors))


@admin_login_required
def topic_edit_ajax(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    if request.method == "GET":
        return JsonResponse({
            "id": str(topic.id), "name": topic.name,
            "description": topic.description or "", "status": topic.status,
        })
    form = TopicEditForm(request.POST, instance=topic)
    if form.is_valid():
        old = {"name": topic.name, "status": topic.status}
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Topic",
                         object_id=topic.id, old_data=old,
                         new_data={"name": obj.name, "status": obj.status})
        return _json_ok(name=obj.name, status=obj.status, message="Topic updated.")
    return _json_err(str(form.errors))


@admin_login_required
@require_POST
def topic_hide_ajax(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    topic.hide()
    create_audit_log(user=request.user, action="HIDE", object_type="Topic", object_id=topic.id)
    return _json_ok(hidden=True, message="Topic and all children hidden.")


@admin_login_required
@require_POST
def topic_unhide_ajax(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    topic.unhide()
    create_audit_log(user=request.user, action="UNHIDE", object_type="Topic", object_id=topic.id)
    return _json_ok(hidden=False, message="Topic unhidden.")


@admin_login_required
@require_POST
def topic_delete_ajax(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    name  = topic.name
    create_audit_log(user=request.user, action="DELETE", object_type="Topic",
                     object_id=topic.id, old_data={"name": name})
    topic.delete()  # CASCADE deletes all children
    return _json_ok(message=f'Topic "{name}" permanently deleted.')


# ── non-AJAX fallbacks (kept for backward compat) ─────────────────────────────

@admin_login_required
def topic_edit(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    form  = TopicEditForm(request.POST or None, instance=topic)
    if request.method == "POST" and form.is_valid():
        old = {"name": topic.name, "status": topic.status}
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Topic",
                         object_id=topic.id, old_data=old,
                         new_data={"name": obj.name, "status": obj.status})
        messages.success(request, "Topic updated.")
        return redirect("admin-dashboard")
    return render(request, "edit_form.html", {
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


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORIES — AJAX CRUD + hide/unhide/delete
# ══════════════════════════════════════════════════════════════════════════════

@user_login_required()
@never_cache
def category_list_view(request):
    is_admin = request.user.is_superuser
    if is_admin:
        qs = Category.objects.select_related("topic").order_by("-created_at")
    else:
        qs = Category.objects.filter(
            status="approved", is_hidden=False, topic__is_hidden=False
        ).select_related("topic").order_by("name")

    paginator = Paginator(qs, 12)
    page_obj  = paginator.get_page(request.GET.get("page", 1))
    fav_ids   = _user_favorite_ids(request.user, "category")

    return render(request, "category_list.html", {
        "categories": page_obj,
        "page_obj":   page_obj,
        "is_admin":   is_admin,
        "fav_ids":    fav_ids,
    })


@user_login_required()
@never_cache
def category_detail_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    is_admin = request.user.is_superuser

    if not is_admin and (category.status != "approved" or category.is_hidden):
        from django.http import Http404
        raise Http404

    if is_admin:
        subcategories = category.subcategories.prefetch_related("questions__answers").order_by("name")
    else:
        subcategories = category.subcategories.filter(
            status="approved", is_hidden=False
        ).prefetch_related("questions__answers").order_by("name")

    fav_cat_ids    = _user_favorite_ids(request.user, "category")
    fav_subcat_ids = _user_favorite_ids(request.user, "subcategory")
    fav_q_ids      = _user_favorite_ids(request.user, "question")

    return render(request, "detail_unified.html", {
        "category":      category,
        "subcategories": subcategories,
        "is_admin":      is_admin,
        "fav_cat_ids":   fav_cat_ids,
        "fav_subcat_ids": fav_subcat_ids,
        "fav_q_ids":     fav_q_ids,
    })


@admin_login_required
def category_create_ajax(request):
    if request.method != "POST":
        return _json_err("POST required", 405)
    form = CategoryForm(request.POST)
    if form.is_valid():
        cat            = form.save(commit=False)
        cat.created_by = request.user
        cat.status     = "approved"
        cat.save()
        create_audit_log(user=request.user, action="CREATE", object_type="Category",
                         object_id=cat.id, new_data={"name": cat.name})
        return _json_ok(id=str(cat.id), name=cat.name, message="Category created.")
    return _json_err(str(form.errors))


@admin_login_required
def category_edit_ajax(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "GET":
        return JsonResponse({
            "id": str(cat.id), "name": cat.name,
            "description": cat.description or "",
            "status": cat.status, "topic_id": str(cat.topic_id),
        })
    form = CategoryEditForm(request.POST, instance=cat)
    if form.is_valid():
        old = {"name": cat.name, "status": cat.status}
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Category",
                         object_id=cat.id, old_data=old,
                         new_data={"name": obj.name, "status": obj.status})
        return _json_ok(name=obj.name, status=obj.status, message="Category updated.")
    return _json_err(str(form.errors))


@admin_login_required
@require_POST
def category_hide_ajax(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    cat.hide()
    create_audit_log(user=request.user, action="HIDE", object_type="Category", object_id=cat.id)
    return _json_ok(hidden=True, message="Category and all children hidden.")


@admin_login_required
@require_POST
def category_unhide_ajax(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    try:
        cat.unhide()
    except ValueError as e:
        return _json_err(str(e))
    create_audit_log(user=request.user, action="UNHIDE", object_type="Category", object_id=cat.id)
    return _json_ok(hidden=False, message="Category unhidden.")


@admin_login_required
@require_POST
def category_delete_ajax(request, pk):
    cat  = get_object_or_404(Category, pk=pk)
    name = cat.name
    create_audit_log(user=request.user, action="DELETE", object_type="Category",
                     object_id=cat.id, old_data={"name": name})
    cat.delete()
    return _json_ok(message=f'Category "{name}" permanently deleted.')


@admin_login_required
def category_edit(request, pk):
    cat  = get_object_or_404(Category, pk=pk)
    form = CategoryEditForm(request.POST or None, instance=cat)
    if request.method == "POST" and form.is_valid():
        old = {"name": cat.name, "status": cat.status}
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Category",
                         object_id=cat.id, old_data=old,
                         new_data={"name": obj.name, "status": obj.status})
        messages.success(request, "Category updated.")
        return redirect("admin-dashboard")
    return render(request, "edit_form.html", {
        "form": form, "title": "Edit Category", "object": cat, "cancel_url": "admin-dashboard",
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


# ══════════════════════════════════════════════════════════════════════════════
# SUBCATEGORIES — AJAX CRUD + hide/unhide/delete
# ══════════════════════════════════════════════════════════════════════════════

@user_login_required()
@never_cache
def subcategory_detail_view(request, pk):
    sub      = get_object_or_404(SubCategory, pk=pk)
    is_admin = request.user.is_superuser

    if not is_admin and (sub.status != "approved" or sub.is_hidden):
        from django.http import Http404
        raise Http404

    if is_admin:
        questions = sub.questions.select_related("created_by").prefetch_related("answers").order_by("-created_at")
    else:
        questions = sub.questions.filter(is_hidden=False).select_related("created_by").prefetch_related("answers").order_by("-created_at")

    paginator = Paginator(questions, 15)
    page_obj  = paginator.get_page(request.GET.get("page", 1))
    fav_q_ids = _user_favorite_ids(request.user, "question")

    return render(request, "detail_unified.html", {
        "subcategory": sub,
        "questions":   page_obj,
        "page_obj":    page_obj,
        "is_admin":    is_admin,
        "fav_q_ids":   fav_q_ids,
    })


@admin_login_required
def subcategory_create_ajax(request):
    if request.method != "POST":
        return _json_err("POST required", 405)
    form = SubCategoryForm(request.POST)
    if form.is_valid():
        sub            = form.save(commit=False)
        sub.created_by = request.user
        sub.status     = "approved"
        sub.save()
        create_audit_log(user=request.user, action="CREATE", object_type="SubCategory",
                         object_id=sub.id, new_data={"name": sub.name})
        return _json_ok(id=str(sub.id), name=sub.name, message="Subcategory created.")
    return _json_err(str(form.errors))


@admin_login_required
def subcategory_edit_ajax(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    if request.method == "GET":
        return JsonResponse({
            "id": str(sub.id), "name": sub.name,
            "status": sub.status, "category_id": str(sub.category_id),
        })
    form = SubCategoryEditForm(request.POST, instance=sub)
    if form.is_valid():
        old = {"name": sub.name, "status": sub.status}
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="SubCategory",
                         object_id=sub.id, old_data=old,
                         new_data={"name": obj.name, "status": obj.status})
        return _json_ok(name=obj.name, status=obj.status, message="Subcategory updated.")
    return _json_err(str(form.errors))


@admin_login_required
@require_POST
def subcategory_hide_ajax(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    sub.hide()
    create_audit_log(user=request.user, action="HIDE", object_type="SubCategory", object_id=sub.id)
    return _json_ok(hidden=True, message="Subcategory and all questions hidden.")


@admin_login_required
@require_POST
def subcategory_unhide_ajax(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    try:
        sub.unhide()
    except ValueError as e:
        return _json_err(str(e))
    create_audit_log(user=request.user, action="UNHIDE", object_type="SubCategory", object_id=sub.id)
    return _json_ok(hidden=False, message="Subcategory unhidden.")


@admin_login_required
@require_POST
def subcategory_delete_ajax(request, pk):
    sub  = get_object_or_404(SubCategory, pk=pk)
    name = sub.name
    create_audit_log(user=request.user, action="DELETE", object_type="SubCategory",
                     object_id=sub.id, old_data={"name": name})
    sub.delete()
    return _json_ok(message=f'Subcategory "{name}" permanently deleted.')


@user_login_required()
def subcategory_create(request, category_pk=None):
    category = None
    if category_pk:
        category = get_object_or_404(Category, pk=category_pk, status="approved")
    form = SubCategoryForm(
        request.POST or None,
        category_pk=str(category.pk) if category else None,
    )
    if request.method == "POST" and form.is_valid():
        obj            = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, "Subcategory submitted for approval.")
        if category:
            return redirect("category-detail", pk=category.pk)
        return redirect("category-list")
    return render(request, "subcategory_create.html", {
        "form": form, "preselected_category": category,
    })


@admin_login_required
def subcategory_edit(request, pk):
    sub  = get_object_or_404(SubCategory, pk=pk)
    form = SubCategoryEditForm(request.POST or None, instance=sub)
    if request.method == "POST" and form.is_valid():
        old = {"name": sub.name, "status": sub.status}
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="SubCategory",
                         object_id=sub.id, old_data=old,
                         new_data={"name": obj.name, "status": obj.status})
        messages.success(request, "Subcategory updated.")
        return redirect("admin-dashboard")
    return render(request, "edit_form.html", {
        "form": form, "title": "Edit Subcategory", "object": sub, "cancel_url": "admin-dashboard",
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


# ══════════════════════════════════════════════════════════════════════════════
# QUESTIONS — AJAX CRUD + hide/unhide/delete
# ══════════════════════════════════════════════════════════════════════════════

@user_login_required()
@never_cache
def question_list_view(request):
    is_admin = request.user.is_superuser
    if is_admin:
        qs = Question.objects.select_related(
            "subcategory__category__topic", "created_by"
        ).prefetch_related("answers").order_by("-created_at")
    else:
        qs = Question.objects.filter(
            is_hidden=False,
            subcategory__is_hidden=False,
            subcategory__category__is_hidden=False,
            subcategory__category__topic__is_hidden=False,
        ).select_related(
            "subcategory__category__topic", "created_by"
        ).prefetch_related("answers").order_by("-created_at")

    q      = request.GET.get("q", "")
    topic  = request.GET.get("topic", "")
    cat    = request.GET.get("category", "")
    subcat = request.GET.get("subcategory", "")

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(normalized_title__icontains=q))
    if topic:
        qs = qs.filter(subcategory__category__topic_id=topic)
    if cat:
        qs = qs.filter(subcategory__category_id=cat)
    if subcat:
        qs = qs.filter(subcategory_id=subcat)

    paginator = Paginator(qs, 15)
    page_obj  = paginator.get_page(request.GET.get("page", 1))
    fav_q_ids = _user_favorite_ids(request.user, "question")

    return render(request, "question_list.html", {
        "questions":       page_obj,
        "page_obj":        page_obj,
        "search_query":    q,
        "filter_topic":    topic,
        "filter_category": cat,
        "filter_subcat":   subcat,
        "topics":          Topic.objects.filter(status="approved").order_by("name"),
        "categories":      Category.objects.filter(status="approved").order_by("name"),
        "subcategories":   SubCategory.objects.filter(status="approved").order_by("name"),
        "is_admin":        is_admin,
        "fav_q_ids":       fav_q_ids,
    })


@user_login_required()
@never_cache
def question_detail_view(request, pk):
    question = get_object_or_404(Question, pk=pk)
    is_admin = request.user.is_superuser

    if not is_admin and question.is_hidden:
        from django.http import Http404
        raise Http404

    Question.objects.filter(pk=question.pk).update(view_count=question.view_count + 1)

    answers = question.answers.prefetch_related("points").select_related("created_by")
    fav_q_ids = _user_favorite_ids(request.user, "question")

    return render(request, "question_detail.html", {
        "question":    question,
        "answers":     answers,
        "answer_form": AnswerForm(),
        "point_form":  AnswerPointForm(),
        "is_admin":    is_admin,
        "fav_q_ids":   fav_q_ids,
    })


@admin_login_required
def question_create_ajax(request):
    if request.method != "POST":
        return _json_err("POST required", 405)
    form = QuestionForm(request.POST)
    if form.is_valid():
        result = create_question(
            user        = request.user,
            subcategory = form.cleaned_data["subcategory"],
            title       = form.cleaned_data["title"],
        )
        if result["success"]:
            create_audit_log(user=request.user, action="CREATE", object_type="Question",
                             object_id=result["question"].id,
                             new_data={"title": result["question"].title})
            return _json_ok(id=str(result["question"].id), message="Question created.")
        dupes = [{"title": str(d["question"])} for d in result["duplicates"]]
        return JsonResponse({"success": False, "duplicates": dupes}, status=409)
    return _json_err(str(form.errors))


@admin_login_required
def question_edit_ajax(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == "GET":
        return JsonResponse({
            "id": str(question.id), "title": question.title,
            "subcategory_id": str(question.subcategory_id),
        })
    form = QuestionEditForm(request.POST, instance=question)
    if form.is_valid():
        from apps.core.services.duplicate_detector import normalize_question as nq
        old              = {"title": question.title}
        obj              = form.save(commit=False)
        obj.normalized_title = nq(obj.title)
        obj.updated_by   = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Question",
                         object_id=question.id, old_data=old, new_data={"title": obj.title})
        return _json_ok(title=obj.title, message="Question updated.")
    return _json_err(str(form.errors))


@admin_login_required
@require_POST
def question_hide_ajax(request, pk):
    question = get_object_or_404(Question, pk=pk)
    question.is_hidden = True
    question.save(update_fields=["is_hidden"])
    create_audit_log(user=request.user, action="HIDE", object_type="Question", object_id=question.id)
    return _json_ok(hidden=True, message="Question hidden.")


@admin_login_required
@require_POST
def question_unhide_ajax(request, pk):
    question = get_object_or_404(Question, pk=pk)
    try:
        question.unhide()
    except ValueError as e:
        return _json_err(str(e))
    create_audit_log(user=request.user, action="UNHIDE", object_type="Question", object_id=question.id)
    return _json_ok(hidden=False, message="Question unhidden.")


@admin_login_required
@require_POST
def question_delete_ajax(request, pk):
    question = get_object_or_404(Question, pk=pk)
    title    = question.title[:80]
    create_audit_log(user=request.user, action="DELETE", object_type="Question",
                     object_id=question.id, old_data={"title": title})
    question.delete()
    return _json_ok(message="Question permanently deleted.")


@user_login_required()
def question_create_view(request):
    form       = QuestionForm(request.POST or None)
    duplicates = []
    if request.method == "POST" and form.is_valid():
        result = create_question(
            user        = request.user,
            subcategory = form.cleaned_data["subcategory"],
            title       = form.cleaned_data["title"],
        )
        if result["success"]:
            create_audit_log(user=request.user, action="CREATE", object_type="Question",
                             object_id=result["question"].id,
                             new_data={"title": result["question"].title})
            messages.success(request, "Question posted successfully.")
            return redirect("question-detail", pk=result["question"].pk)
        else:
            duplicates = result["duplicates"]
            messages.warning(request, "Similar questions already exist.")
    return render(request, "question_create.html", {
        "form": form, "duplicates": duplicates,
    })


@user_login_required("core.bulk_upload_question")
def bulk_qa_upload(request):
    form   = BulkQAUploadForm(request.POST or None)
    report = None

    if request.method == "POST" and form.is_valid():
        subcategory = form.cleaned_data["subcategory"]
        raw_text    = form.cleaned_data["raw_text"]

        session = BulkUploadSession.objects.create(
            uploaded_by = request.user,
            topic       = form.cleaned_data["topic"],
            category    = form.cleaned_data["category"],
            subcategory = subcategory,
            raw_text    = raw_text,
        )
        report = process_bulk_upload(
            user        = request.user,
            subcategory = subcategory,
            raw_text    = raw_text,
            session     = session,
        )

        if report["questions_created"] > 0:
            messages.success(
                request,
                f"✓ {report['questions_created']} question(s) and "
                f"{report['answers_created']} answer(s) uploaded successfully.",
            )
        if report["duplicates_skipped"]:
            for dup in report["duplicates_skipped"]:
                messages.warning(
                    request,
                    f'"{dup["question"]}" already exists. Please cross-check the answers.',
                )
        if report.get("errors"):
            messages.error(request, f"✗ {len(report['errors'])} error(s) occurred.")
        form = BulkQAUploadForm()

    return render(request, "bulk_qa_upload.html", {
        "form": form, "report": report,
    })


@admin_login_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk)
    form     = QuestionEditForm(request.POST or None, instance=question)
    if request.method == "POST" and form.is_valid():
        from apps.core.services.duplicate_detector import normalize_question as nq
        old              = {"title": question.title}
        obj              = form.save(commit=False)
        obj.normalized_title = nq(obj.title)
        obj.updated_by   = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Question",
                         object_id=question.id, old_data=old, new_data={"title": obj.title})
        messages.success(request, "Question updated.")
        return redirect("question-detail", pk=obj.pk)
    return render(request, "edit_form.html", {
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


# ══════════════════════════════════════════════════════════════════════════════
# ANSWERS
# ══════════════════════════════════════════════════════════════════════════════

@user_login_required()
def answer_create_view(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    form     = AnswerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        content = form.cleaned_data["content"]
        if is_duplicate_answer(content, question_pk):
            messages.warning(request, "A very similar answer already exists.")
            return render(request, "answer_create.html", {
                "form": form, "question": question,
            })
        answer            = form.save(commit=False)
        answer.question   = question
        answer.created_by = request.user
        answer.save()
        create_audit_log(user=request.user, action="CREATE", object_type="Answer",
                         object_id=answer.id, new_data={"question": str(question.id)})
        messages.success(request, "Answer posted.")
        return redirect("question-detail", pk=question.pk)
    return render(request, "answer_create.html", {
        "form": form, "question": question,
    })


@admin_login_required
def answer_edit(request, pk):
    answer = get_object_or_404(Answer, pk=pk)
    form   = AnswerEditForm(request.POST or None, instance=answer)
    if request.method == "POST" and form.is_valid():
        old    = {"content": answer.content}
        obj    = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        create_audit_log(user=request.user, action="EDIT", object_type="Answer",
                         object_id=answer.id, old_data=old,
                         new_data={"content": answer.content[:100]})
        messages.success(request, "Answer updated.")
        return redirect("question-detail", pk=answer.question.pk)
    return render(request, "edit_form.html", {
        "form": form, "title": "Edit Answer", "object": answer,
        "cancel_href": f"/questions/{answer.question.pk}/",
    })


@admin_login_required
def answer_delete(request, pk):
    answer      = get_object_or_404(Answer, pk=pk)
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


@user_login_required()
def answer_point_create_view(request, answer_pk):
    answer = get_object_or_404(Answer, pk=answer_pk)
    form   = AnswerPointForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        point            = form.save(commit=False)
        point.answer     = answer
        point.created_by = request.user
        point.save()
        messages.success(request, "Key point added.")
        return redirect("question-detail", pk=answer.question.pk)
    return render(request, "answerpoint_create.html", {
        "form": form, "answer": answer,
    })


# ══════════════════════════════════════════════════════════════════════════════
# USER DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@user_login_required()
@never_cache
def user_dashboard(request):
    if request.user.is_superuser:
        return redirect("admin-dashboard")
    user            = request.user
    notification_qs = Notification.objects.filter(user=user)

    return render(request, "user_dashboard.html", {
        "my_questions":    Question.objects.filter(created_by=user).order_by("-created_at")[:5],
        "my_answers":      Answer.objects.filter(created_by=user).select_related("question").order_by("-created_at")[:5],
        "my_bulk_uploads": BulkUploadSession.objects.filter(uploaded_by=user).order_by("-created_at")[:5],
        "my_topics":       Topic.objects.filter(created_by=user).order_by("-created_at")[:5],
        "notifications":   notification_qs.order_by("-created_at")[:10],
        "unread_count":    notification_qs.filter(is_read=False).count(),
        "total_questions": Question.objects.filter(created_by=user).count(),
        "total_answers":   Answer.objects.filter(created_by=user).count(),
        "total_favorites": Favorite.objects.filter(user=user).count(),
    })


@user_login_required()
def mark_notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER", "/dashboard/"))


@user_login_required()
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("user-dashboard")


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

@admin_login_required
def audit_log_view(request):
    logs          = AuditLog.objects.select_related("user").order_by("-created_at")
    action_filter = request.GET.get("action", "")
    type_filter   = request.GET.get("type",   "")
    if action_filter:
        logs = logs.filter(action=action_filter)
    if type_filter:
        logs = logs.filter(object_type=type_filter)
    page = Paginator(logs, 30).get_page(request.GET.get("page", 1))
    return render(request, "audit_log.html", {
        "page":          page,
        "action_filter": action_filter,
        "type_filter":   type_filter,
        "actions": AuditLog.objects.values_list("action", flat=True).distinct(),
        "types":   AuditLog.objects.values_list("object_type", flat=True).distinct(),
    })


@admin_login_required
def admin_content_view(request):
    tab = request.GET.get("tab", "topics")
    return redirect(f"/admin-dashboard/?tab={tab}")


@admin_login_required
def user_list_view(request):
    from apps.core.models import CustomUser, Role
    return render(request, "user_list.html", {
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