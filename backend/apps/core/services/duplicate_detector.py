import re

try:
    from nltk.corpus import stopwords
    STOP_WORDS = set(stopwords.words("english"))
except Exception:
    STOP_WORDS = {
        "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "not", "with", "this", "that", "what",
        "how", "why", "when", "where", "who", "which", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
    }


def normalize_question(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    words = [w for w in text.split() if w not in STOP_WORDS]
    return " ".join(words)


def find_similar_questions(question_text: str, threshold: int = 85) -> list:
    from apps.core.models import Question
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        return []

    normalized = normalize_question(question_text)
    if not normalized:
        return []

    matches = []
    for q in Question.objects.exclude(normalized_title__isnull=True).exclude(normalized_title=""):
        score = fuzz.ratio(normalized, q.normalized_title)
        if score >= threshold:
            matches.append({"question": q, "score": score})

    return sorted(matches, key=lambda x: x["score"], reverse=True)

