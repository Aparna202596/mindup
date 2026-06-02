import re
from fuzzywuzzy import fuzz
from apps.questions.models import Question
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words("english"))


def normalize_question(text):

    text = text.lower().strip()

    text = re.sub(r"[^\w\s]", "", text)

    words = text.split()

    filtered = [
        word
        for word in words
        if word not in STOP_WORDS
    ]

    return " ".join(filtered)

def find_similar_questions(question_text):

    normalized = normalize_question(question_text)

    matches = []

    existing_questions = Question.objects.all()

    for question in existing_questions:

        score = fuzz.ratio(
            normalized,
            question.normalized_title
        )

        if score >= 85:

            matches.append({
                "question": question,
                "score": score
            })

    return matches