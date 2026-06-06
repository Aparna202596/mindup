import logging
from django.db.models import Q, Value, FloatField
from django.contrib.postgres.search import (
    SearchVector, SearchQuery, SearchRank, TrigramSimilarity
)
from apps.core.models import Question, Topic, Category, SubCategory

logger = logging.getLogger(__name__)


def global_search(query: str, limit: int = 20) -> dict:
    """
    Three-tier search:
    1. PostgreSQL full-text search on search_vector (fastest, most relevant)
    2. Trigram similarity on title (handles typos)
    3. icontains fallback (always works)
    """
    if not query or not query.strip():
        return {"questions": [], "topics": [], "categories": []}

    query = query.strip()

    questions = _search_questions(query, limit)
    topics    = _search_topics(query)
    categories = _search_categories(query)

    return {
        "questions":  questions,
        "topics":     topics,
        "categories": categories,
        "query":      query,
    }


def _search_questions(query: str, limit: int):
    try:
        # Full-text search with ranking
        search_query = SearchQuery(query, config="english")
        qs = (
            Question.objects
            .annotate(rank=SearchRank("search_vector", search_query))
            .filter(rank__gt=0.01)
            .select_related("subcategory__category__topic")
            .order_by("-rank")[:limit]
        )
        results = list(qs)

        # Supplement with trigram if full-text returned few results
        if len(results) < 5:
            trgm_qs = (
                Question.objects
                .annotate(similarity=TrigramSimilarity("title", query))
                .filter(similarity__gt=0.15)
                .exclude(id__in=[q.id for q in results])
                .select_related("subcategory__category__topic")
                .order_by("-similarity")[:limit - len(results)]
            )
            results = results + list(trgm_qs)

        # Final fallback
        if not results:
            results = list(
                Question.objects
                .filter(Q(title__icontains=query) | Q(normalized_title__icontains=query))
                .select_related("subcategory__category__topic")
                .order_by("-view_count")[:limit]
            )

        return results

    except Exception as e:
        logger.warning(f"Full-text search failed, using fallback: {e}")
        return list(
            Question.objects
            .filter(Q(title__icontains=query))
            .select_related("subcategory__category__topic")
            .order_by("-view_count")[:limit]
        )


def _search_topics(query: str) -> list:
    try:
        return list(
            Topic.objects
            .annotate(similarity=TrigramSimilarity("name", query))
            .filter(Q(similarity__gt=0.1) | Q(name__icontains=query), status="approved")
            .order_by("-similarity")[:5]
        )
    except Exception:
        return list(Topic.objects.filter(name__icontains=query, status="approved")[:5])


def _search_categories(query: str) -> list:
    try:
        return list(
            Category.objects
            .filter(Q(name__icontains=query), status="approved")
            .select_related("topic")[:5]
        )
    except Exception:
        return []


def rebuild_search_vectors():
    """
    One-time rebuild of all search vectors.
    Call from shell or management command after bulk imports.
    """
    from django.contrib.postgres.search import SearchVector
    updated = Question.objects.update(
        search_vector=SearchVector("title", "normalized_title", config="english")
    )
    logger.info(f"Rebuilt search vectors for {updated} questions")
    return updated