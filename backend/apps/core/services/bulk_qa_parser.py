import re
import logging

logger = logging.getLogger(__name__)

# ── Public entry point ─────────────────────────────────────────────────────────

def parse_bulk_text(raw_text: str) -> list[dict]:
    """
    Parse pasted text into a list of {"question": str, "answer": str} dicts.
    Tries parsers in order; returns first non-empty result.
    """
    text = raw_text.strip()
    for strategy in [
        _parse_explicit_qa_markers,
        _parse_numbered_with_answer_label,
        _parse_numbered_pairs,
        _parse_paragraph_pairs,
    ]:
        try:
            results = strategy(text)
            if results:
                logger.info(
                    "bulk_qa_parser: %s extracted %d pairs",
                    strategy.__name__, len(results)
                )
                return results
        except Exception as e:
            logger.warning("Parser %s failed: %s", strategy.__name__, e)
    return []


# ── Strategy 1: Q: / A: markers (ChatGPT-style output) ───────────────────────

def _parse_explicit_qa_markers(text: str) -> list[dict]:
    """
    Handles:
        Q: What is X?
        A: X is ...

        Question: What is Y?
        Answer: Y is ...

        Q1: What is Z?
        A1: Z is ...
    """
    pattern = re.compile(
        r'(?:^|\n)\s*(?:Q(?:uestion)?\s*\d*\s*[:\.\)]\s*)(.+?)(?:\n)'
        r'\s*(?:A(?:nswer)?\s*\d*\s*[:\.\)]\s*)([\s\S]+?)(?=\n\s*(?:Q(?:uestion)?\s*\d*\s*[:\.\)])|$)',
        re.IGNORECASE
    )
    results = []
    for m in pattern.finditer('\n' + text):
        q = m.group(1).strip()
        a = m.group(2).strip()
        if q and a:
            results.append({"question": q, "answer": a})
    return results


# ── Strategy 2: Q1. question\nAnswer: answer  ─────────────────────────────────

def _parse_numbered_with_answer_label(text: str) -> list[dict]:
    """
    Handles:
        Q1. What is Python?
        Answer: Python is a high-level language...

        1. What is Django?
        Answer:
        Django is a web framework...
    """
    chunks = re.split(
        r'\n\s*(?:Q\s*\d+[\.\):]|Question\s*\d+[\.\):]|\d+[\.\)])\s+',
        '\n' + text,
        flags=re.IGNORECASE
    )
    results = []
    for chunk in chunks[1:]:
        parts = re.split(r'\n\s*(?:Answer\s*[:\-]?\s*)', chunk, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            q = parts[0].strip().rstrip('?') + '?'
            a = parts[1].strip()
            if len(q) >= 5 and len(a) >= 3:
                results.append({"question": q, "answer": a})
    return results


# ── Strategy 3: Numbered Q no explicit answer label ──────────────────────────

def _parse_numbered_pairs(text: str) -> list[dict]:
    """
    Handles:
        1. What is X?
        X is a thing that does Y. It has Z properties.

        2. What is Y?
        Y is another thing.
    """
    lines = text.split('\n')
    results = []
    i = 0
    while i < len(lines):
        m = re.match(r'^\s*\d+[\.\)]\s+(.{10,})', lines[i])
        if m:
            question = m.group(1).strip()
            answer_lines = []
            j = i + 1
            while j < len(lines):
                stripped = lines[j].strip()
                if re.match(r'^\d+[\.\)]\s+', stripped):
                    break
                if stripped:
                    answer_lines.append(lines[j])
                elif answer_lines:
                    break
                j += 1
            answer = '\n'.join(answer_lines).strip()
            if question and len(answer) >= 3:
                results.append({"question": question, "answer": answer})
            i = j
        else:
            i += 1
    return results


# ── Strategy 4: Paragraph pairs ──────────────────────────────────────────────

def _parse_paragraph_pairs(text: str) -> list[dict]:
    """
    Handles double-blank-line separated Q&A pairs where every odd paragraph
    is a question and every even paragraph is an answer.
    """
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    results = []
    for i in range(0, len(paragraphs) - 1, 2):
        q = paragraphs[i]
        a = paragraphs[i + 1]
        if len(q) >= 10 and len(a) >= 3:
            results.append({"question": q, "answer": a})
    return results


# ── Bulk save entry point ─────────────────────────────────────────────────────

def process_bulk_upload(
    *,
    user,
    subcategory,
    raw_text: str,
    session=None,     # optional BulkUploadSession to update
) -> dict:
    """
    Parse raw_text, check duplicates, save valid Q&A pairs.
    Returns report dict.
    """
    from django.db import transaction
    from apps.core.models import Question, Answer
    from apps.core.services.duplicate_detector import (
        normalize_question, find_similar_questions
    )
    from apps.core.services.audit_service import create_audit_log

    pairs = parse_bulk_text(raw_text)
    report = {
        "total_parsed": len(pairs),
        "questions_created": 0,
        "answers_created": 0,
        "duplicates_skipped": [],   # list of {"question": str, "existing": str}
        "errors": [],
    }

    if not pairs:
        report["errors"].append("Could not detect any Q&A pairs in the pasted text.")
        return report

    for pair in pairs:
        q_text = pair["question"].strip()
        a_text = pair["answer"].strip()

        if not q_text or len(q_text) < 5:
            continue

        try:
            # ── Duplicate check ──────────────────────────────────────────────
            dupes = find_similar_questions(q_text, threshold=88)
            # Also check exact match within same subcategory
            exact = Question.objects.filter(
                subcategory=subcategory,
                normalized_title=normalize_question(q_text)
            ).first()

            if exact or dupes:
                matched = exact or dupes[0]["question"]
                report["duplicates_skipped"].append({
                    "question": q_text[:120],
                    "existing": str(matched)[:120],
                })
                continue

            # ── Save ─────────────────────────────────────────────────────────
            with transaction.atomic():
                question = Question.objects.create(
                    subcategory=subcategory,
                    title=q_text,
                    normalized_title=normalize_question(q_text),
                    created_by=user,
                )
                report["questions_created"] += 1

                if a_text:
                    Answer.objects.create(
                        question=question,
                        content=a_text,   # preserved exactly
                        created_by=user,
                    )
                    report["answers_created"] += 1

                create_audit_log(
                    user=user,
                    action="BULK_UPLOAD",
                    object_type="Question",
                    object_id=question.id,
                    new_data={"title": q_text[:80], "subcategory": str(subcategory)},
                )

        except Exception as e:
            logger.exception("Error saving bulk pair: %s", e)
            report["errors"].append(f"Error saving '{q_text[:60]}': {e}")

    # ── Update session record ─────────────────────────────────────────────────
    if session:
        session.questions_created  = report["questions_created"]
        session.duplicates_skipped = len(report["duplicates_skipped"])
        session.errors_count       = len(report["errors"])
        session.processing_report  = _format_report(report)
        session.save()

    return report


def _format_report(report: dict) -> str:
    lines = [
        f"Parsed:    {report['total_parsed']} pairs",
        f"Created:   {report['questions_created']} questions, {report['answers_created']} answers",
        f"Skipped:   {len(report['duplicates_skipped'])} duplicates",
    ]
    for d in report["duplicates_skipped"][:20]:
        lines.append(f"  DUPLICATE: \"{d['question']}\" → already exists as \"{d['existing']}\"")
    if report["errors"]:
        lines.append(f"Errors: {len(report['errors'])}")
        for e in report["errors"][:10]:
            lines.append(f"  ERROR: {e}")
    return '\n'.join(lines)