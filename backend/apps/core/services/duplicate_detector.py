import re
import logging

logger = logging.getLogger(__name__)

# ── Stop words (fallback if NLTK not available) ────────────────────────────────
try:
    from nltk.corpus import stopwords as _sw
    STOP_WORDS = set(_sw.words("english"))
except Exception:
    STOP_WORDS = {
        "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "not", "with", "this", "that", "what",
        "how", "why", "when", "where", "who", "which", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "can", "could", "should", "may", "might", "shall",
        "about", "from", "into", "through", "during", "before", "after",
        "above", "below", "up", "down", "out", "off", "over", "under",
        "then", "than", "so", "if", "while",
    }


# ── Normalisation ──────────────────────────────────────────────────────────────

def normalize_question(text: str) -> str:
    """
    Lowercase → strip punctuation → remove stop words → collapse spaces.
    The result is stored in Question.normalized_title for fast comparisons.
    """
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)          # remove punctuation
    text = re.sub(r"\s+", " ", text)             # collapse whitespace
    words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


# ── Question duplicate detection ───────────────────────────────────────────────

def find_similar_questions(question_text: str, threshold: int = 85) -> list:
    """
    Returns a sorted list of {"question": <Question>, "score": int}.

    Strategy (in order of preference):
      1. PostgreSQL trigram similarity  (fast, DB-side)
      2. RapidFuzz token_sort_ratio     (handles word-order differences)
      3. RapidFuzz simple ratio         (exact character similarity)
    """
    from apps.core.models import Question

    normalized = normalize_question(question_text)
    if not normalized or len(normalized) < 5:
        return []

    matches = []

    # ── Try DB-side trigram first (much faster on large datasets) ──────────────
    try:
        from django.contrib.postgres.search import TrigramSimilarity
        from django.db.models import FloatField
        from django.db.models.functions import Cast

        qs = (
            Question.objects
            .annotate(sim=TrigramSimilarity("normalized_title", normalized))
            .filter(sim__gte=(threshold - 15) / 100)   # slightly looser for trigram
            .select_related("subcategory__category__topic")
            .order_by("-sim")[:50]
        )
        for q in qs:
            # Refine with RapidFuzz for a more accurate score
            score = _fuzzy_score(normalized, q.normalized_title or "")
            if score >= threshold:
                matches.append({"question": q, "score": score})

        if matches:
            return sorted(matches, key=lambda x: x["score"], reverse=True)

    except Exception as exc:
        logger.debug("Trigram query failed (%s), falling back to Python scan", exc)

    # ── Full Python scan fallback (small datasets / no pg_trgm extension) ──────
    try:
        for q in Question.objects.exclude(normalized_title__isnull=True).exclude(normalized_title=""):
            score = _fuzzy_score(normalized, q.normalized_title)
            if score >= threshold:
                matches.append({"question": q, "score": score})
    except Exception as exc:
        logger.warning("Duplicate detection failed: %s", exc)

    return sorted(matches, key=lambda x: x["score"], reverse=True)


def _fuzzy_score(a: str, b: str) -> int:
    """Return best RapidFuzz score between two normalised strings."""
    try:
        from rapidfuzz import fuzz
        return max(
            fuzz.ratio(a, b),
            fuzz.token_sort_ratio(a, b),
            fuzz.token_set_ratio(a, b),
        )
    except ImportError:
        pass

    try:
        from fuzzywuzzy import fuzz
        return max(fuzz.ratio(a, b), fuzz.token_sort_ratio(a, b))
    except ImportError:
        pass

    # Naïve fallback: word overlap
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return int(intersection / union * 100)


# ── Answer duplicate detection ─────────────────────────────────────────────────

def is_duplicate_answer(answer_text: str, question_id, threshold: int = 90) -> bool:
    """
    Returns True if a very similar answer already exists for this question.
    Prevents users from adding the same answer twice.
    """
    from apps.core.models import Answer

    normalized_new = normalize_question(answer_text)  # same normaliser works for answers
    if not normalized_new:
        return False

    existing = Answer.objects.filter(question_id=question_id)
    for ans in existing:
        score = _fuzzy_score(normalized_new, normalize_question(ans.content))
        if score >= threshold:
            return True
    return False
