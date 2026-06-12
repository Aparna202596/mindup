import re
import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC: parse entry point
# ══════════════════════════════════════════════════════════════════════════════

def parse_bulk_text(raw_text: str) -> list[dict]:

    text = raw_text.strip()
    if not text:
        return []

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
                    "bulk_qa_parser (%s): extracted %d pairs",
                    strategy.__name__, len(results),
                )
                return results
        except Exception as exc:
            logger.warning("Parser %s raised: %s", strategy.__name__, exc)

    logger.warning("bulk_qa_parser: no strategy matched — 0 pairs extracted")
    return []


# ══════════════════════════════════════════════════════════════════════════════
# Strategy 1 — Explicit Q: / A: markers
# ══════════════════════════════════════════════════════════════════════════════

_EXPLICIT_Q = re.compile(
    r"(?:^|\n)\s*Q(?:uestion)?\s*\d*\s*[:\.\)]\s*",
    re.IGNORECASE,
)
_EXPLICIT_A = re.compile(
    r"\n\s*A(?:nswer)?\s*\d*\s*[:\.\)]\s*",
    re.IGNORECASE,
)

def _parse_explicit_qa_markers(text: str) -> list[dict]:

    # Split on Q: / Question: markers
    q_parts = _EXPLICIT_Q.split("\n" + text)
    results = []

    for part in q_parts[1:]:
        # Split on A: / Answer: marker (first occurrence only)
        a_parts = _EXPLICIT_A.split(part, maxsplit=1)
        if len(a_parts) != 2:
            continue

        question = a_parts[0].strip()
        # Trim trailing next Q: marker from the answer (if any)
        answer_raw = _EXPLICIT_Q.split(a_parts[1])[0].strip()

        if len(question) >= 5 and len(answer_raw) >= 2:
            results.append({"question": question, "answer": answer_raw})

    return results


# ══════════════════════════════════════════════════════════════════════════════
# Strategy 2 — Numbered questions with explicit "Answer:" label
# ══════════════════════════════════════════════════════════════════════════════

_NUM_Q = re.compile(
    r"(?:^|\n)\s*(?:Q\s*\d+[\.\):]|Question\s*\d+[\.\):]|\d+[\.\)])\s+",
    re.IGNORECASE,
)
_NUM_A_LABEL = re.compile(
    r"\n\s*A(?:nswer)?\s*\d*\s*[:\-]\s*",
    re.IGNORECASE,
)

def _parse_numbered_with_answer_label(text: str) -> list[dict]:

    q_parts = _NUM_Q.split("\n" + text)
    results = []

    for part in q_parts[1:]:
        a_parts = _NUM_A_LABEL.split(part, maxsplit=1)
        if len(a_parts) != 2:
            continue
        question = a_parts[0].strip()
        answer   = _NUM_Q.split(a_parts[1])[0].strip()
        if len(question) >= 5 and len(answer) >= 2:
            results.append({"question": question, "answer": answer})

    return results


# ══════════════════════════════════════════════════════════════════════════════
# Strategy 3 — Numbered pairs (no explicit Answer: label)
# ══════════════════════════════════════════════════════════════════════════════

_NUMBERED_LINE = re.compile(r"^\s*(\d+)[\.\)]\s+(.{5,})")

def _parse_numbered_pairs(text: str) -> list[dict]:

    lines   = text.split("\n")
    results = []
    i       = 0

    while i < len(lines):
        m = _NUMBERED_LINE.match(lines[i])
        if m:
            question     = m.group(2).strip()
            answer_lines = []
            j = i + 1
            while j < len(lines):
                stripped = lines[j].strip()
                if _NUMBERED_LINE.match(lines[j]):
                    break
                if stripped:
                    answer_lines.append(lines[j])
                elif answer_lines:
                    # Allow one blank line inside an answer block
                    if j + 1 < len(lines) and lines[j + 1].strip():
                        answer_lines.append("")
                    else:
                        break
                j += 1

            answer = "\n".join(answer_lines).strip()
            if question and len(answer) >= 2:
                results.append({"question": question, "answer": answer})
            i = j
        else:
            i += 1

    return results


# ══════════════════════════════════════════════════════════════════════════════
# Strategy 4 — Blank-line paragraph pairs
# ══════════════════════════════════════════════════════════════════════════════

def _parse_paragraph_pairs(text: str) -> list[dict]:

    paragraphs = [
        p.strip()
        for p in re.split(r"\n{2,}", text)
        if p.strip() and len(p.strip()) >= 5
    ]
    results = []
    for i in range(0, len(paragraphs) - 1, 2):
        q = paragraphs[i]
        a = paragraphs[i + 1]
        if len(q) >= 5 and len(a) >= 2:
            results.append({"question": q, "answer": a})
    return results


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC: bulk save entry point
# ══════════════════════════════════════════════════════════════════════════════

def process_bulk_upload(
    *,
    user,
    subcategory,
    raw_text: str,
    session=None,
) -> dict:

    from django.db import transaction
    from apps.core.models import Question, Answer
    from apps.core.services.duplicate_detector import (
        normalize_question,
        find_similar_questions,
    )
    from apps.core.services.audit_service import create_audit_log

    pairs = parse_bulk_text(raw_text)

    report: dict = {
        "total_parsed":       len(pairs),
        "questions_created":  0,
        "answers_created":    0,
        "duplicates_skipped": [],   # [{"question": str, "existing": str}]
        "errors":             [],
    }

    if not pairs:
        report["errors"].append(
            "Could not detect any Q&A pairs. "
            "Try using Q:/A: markers or numbered questions."
        )
        _update_session(session, report)
        return report

    for pair in pairs:
        q_text = pair["question"].strip()
        a_text = pair["answer"].strip()

        if len(q_text) < 5:
            continue

        try:
            # ── Exact duplicate within same subcategory ──────────────────────
            norm = normalize_question(q_text)
            exact = Question.objects.filter(
                subcategory=subcategory,
                normalized_title=norm,
            ).first()

            # ── Fuzzy duplicate across the whole DB ──────────────────────────
            fuzzy_dupes = [] if exact else find_similar_questions(q_text, threshold=88)

            if exact or fuzzy_dupes:
                matched_title = str(exact or fuzzy_dupes[0]["question"])
                report["duplicates_skipped"].append({
                    "question": q_text[:150],
                    "existing": matched_title[:150],
                })
                continue

            # ── Save ─────────────────────────────────────────────────────────
            with transaction.atomic():
                question = Question.objects.create(
                    subcategory      = subcategory,
                    title            = q_text,
                    normalized_title = norm,
                    created_by       = user,
                )
                report["questions_created"] += 1

                if a_text:
                    Answer.objects.create(
                        question   = question,
                        content    = a_text,   # ← preserved exactly
                        created_by = user,
                    )
                    report["answers_created"] += 1

                create_audit_log(
                    user        = user,
                    action      = "BULK_UPLOAD",
                    object_type = "Question",
                    object_id   = question.id,
                    new_data    = {
                        "title":       q_text[:100],
                        "subcategory": str(subcategory),
                        "session_id":  str(session.id) if session else None,
                    },
                )

        except Exception as exc:
            logger.exception("bulk_qa_parser: error saving pair '%s': %s", q_text[:60], exc)
            report["errors"].append(f"'{q_text[:60]}': {exc}")

    _update_session(session, report)
    return report


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _update_session(session, report: dict) -> None:
    if not session:
        return
    session.questions_created  = report["questions_created"]
    session.duplicates_skipped = len(report["duplicates_skipped"])
    session.errors_count       = len(report["errors"])
    session.processing_report  = _format_report(report)
    session.save(update_fields=[
        "questions_created", "duplicates_skipped",
        "errors_count", "processing_report",
    ])


def _format_report(report: dict) -> str:
    lines = [
        f"Parsed:    {report['total_parsed']} pairs",
        f"Created:   {report['questions_created']} questions, "
        f"{report['answers_created']} answers",
        f"Skipped:   {len(report['duplicates_skipped'])} duplicates",
    ]
    for d in report["duplicates_skipped"][:30]:
        lines.append(f'  DUPLICATE: "{d["question"]}" → "{d["existing"]}"')
    if report["errors"]:
        lines.append(f"Errors:    {len(report['errors'])}")
        for e in report["errors"][:10]:
            lines.append(f"  ERROR: {e}")
    return "\n".join(lines)