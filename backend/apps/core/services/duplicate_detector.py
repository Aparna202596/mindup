import re
from fuzzywuzzy import fuzz

try:
    from nltk.corpus import stopwords
    STOP_WORDS = set(stopwords.words("english"))
except Exception:
    STOP_WORDS = set()


def normalize_question(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    words = [w for w in text.split() if w not in STOP_WORDS]
    return " ".join(words)


def find_similar_questions(question_text, threshold=85):
    from apps.core.models import Question
    normalized = normalize_question(question_text)
    matches = []
    for q in Question.objects.exclude(normalized_title__isnull=True):
        score = fuzz.ratio(normalized, q.normalized_title)
        if score >= threshold:
            matches.append({"question": q, "score": score})
    return sorted(matches, key=lambda x: x["score"], reverse=True)