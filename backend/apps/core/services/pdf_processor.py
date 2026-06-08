import re
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def process_pdf(upload_id: str) -> dict:
    from apps.core.models import PDFUpload

    try:
        upload = PDFUpload.objects.get(id=upload_id)
    except PDFUpload.DoesNotExist:
        return {"error": "Upload not found"}

    upload.process_status = "processing"
    upload.save(update_fields=["process_status"])

    report = {
        "questions_created": 0,
        "answers_created": 0,
        "answer_points_created": 0,
        "duplicates_skipped": 0,
        "topics_created": 0,
        "categories_created": 0,
        "subcategories_created": 0,
        "errors": [],
    }

    try:
        text = _extract_text(upload.file.path)
        if not text.strip():
            raise ValueError("No readable text found in PDF.")

        # ── 1. Try the structured format (Topic / Category / SubCat / Q&A)
        blocks = _parse_structured(text)

        # ── 2. Fall back to flat Q&A parsers
        if not blocks:
            flat_sections = _parse_flat(text)
            if not flat_sections:
                raise ValueError(
                    "Could not detect Q&A structure. "
                    "Use 'Q:' / 'A:' markers, numbered questions, "
                    "or a Topic / Category / Subcategory header block."
                )
            subcategory = _get_or_create_pdf_subcategory(upload.uploaded_by)
            blocks = [{"subcategory_obj": subcategory, "sections": flat_sections}]

        user = upload.uploaded_by

        for block in blocks:
            sub = block["subcategory_obj"]
            for section in block["sections"]:
                try:
                    _save_section(section, user, sub, report)
                except Exception as exc:
                    report["errors"].append(str(exc))
                    logger.exception("Error saving section: %s", exc)

        # Also create approval queue entries for new topic/cat/subcat created
        # (they are set approved=True when admin creates them; user-created ones
        #  will go through normal signal-triggered approval)

        upload.process_status = "completed"
        upload.processing_report = _format_report(report)

    except Exception as exc:
        logger.exception("PDF processing failed: %s", exc)
        upload.process_status = "failed"
        upload.processing_report = f"Processing failed: {exc}"

    upload.save(update_fields=["process_status", "processing_report"])
    return report


# ──────────────────────────────────────────────────────────────────────────────
# TEXT EXTRACTION
# ──────────────────────────────────────────────────────────────────────────────

def _extract_text(file_path: str) -> str:
    try:
        import pypdf
        parts = []
        with open(file_path, "rb") as fh:
            reader = pypdf.PdfReader(fh)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts)
    except ImportError:
        raise ValueError("pypdf not installed. Run: pip install pypdf")
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# STRUCTURED PARSER  (Topic → Category → Subcategory → Q&A)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_structured(text: str) -> list:
    """
    Returns a list of block-dicts:
      [{"subcategory_obj": <SubCategory>, "sections": [{"question":…, "bullets":[…]}, …]}, …]

    Heuristic:
      • The first 1-3 short lines (≤60 chars) before the first question marker
        are treated as Topic / Category / Subcategory headers.
      • Question markers: "Q1." / "Q." / "Question 1." / "1."
      • Answer section ends at next question marker.
      • Bullet markers: "·", "•", "-", "*", or lines that start with a digit+dot
        inside an answer block.
    """
    lines = [ln.rstrip() for ln in text.split("\n")]

    # ── find first question line index
    q_pattern = re.compile(
        r'^\s*(?:Q\s*\d*[\.\):]|Question\s*\d*[\.\):]|\d+[\.\)])\s+\S',
        re.IGNORECASE
    )
    first_q_idx = next((i for i, ln in enumerate(lines) if q_pattern.match(ln)), None)
    if first_q_idx is None:
        return []          # no question markers → fall back to flat parsers

    # ── header lines = non-empty lines before first question, limited to 5
    header_lines = [ln.strip() for ln in lines[:first_q_idx] if ln.strip()][-5:]

    # ── resolve topic / category / subcategory from headers
    topic_name, category_name, subcat_name = _resolve_headers(header_lines)

    # ── get or create the hierarchy (admin-approved immediately)
    from apps.core.models import Topic, Category, SubCategory

    # We use a sentinel user (system) here; the signal will NOT fire for
    # status=approved objects created below because we pass skip_signal=True
    # via a queryset update instead of save().

    topic, t_created = _get_or_create_approved(Topic, {"name": topic_name})
    category, c_created = _get_or_create_approved(
        Category, {"topic": topic, "name": category_name}
    )
    subcat, s_created = _get_or_create_approved(
        SubCategory, {"category": category, "name": subcat_name}
    )

    # ── parse all questions in the remaining lines
    sections = _extract_qa_blocks(lines[first_q_idx:])
    if not sections:
        return []

    return [{
        "subcategory_obj": subcat,
        "sections": sections,
        "_new_topic": t_created,
        "_new_cat": c_created,
        "_new_sub": s_created,
    }]


def _resolve_headers(header_lines: list) -> tuple:
    """
    Given up to 5 header lines, return (topic, category, subcategory).
    Falls back to sensible defaults when fewer lines are present.
    """
    cleaned = [h for h in header_lines if h]
    if len(cleaned) >= 3:
        return cleaned[-3], cleaned[-2], cleaned[-1]
    elif len(cleaned) == 2:
        return cleaned[0], cleaned[0], cleaned[1]
    elif len(cleaned) == 1:
        return cleaned[0], cleaned[0], cleaned[0]
    else:
        return "PDF Imports", "Imported Content", "PDF Extracted"


def _get_or_create_approved(Model, lookup: dict):
    """
    Get or create a Topic/Category/SubCategory with status=approved.
    Does NOT trigger the approval-queue signal (we set status directly in DB).
    """
    from apps.core.models import CustomUser

    # Find a superuser to act as system creator; fall back to first user.
    system_user = (
        CustomUser.objects.filter(is_superuser=True).first()
        or CustomUser.objects.first()
    )

    defaults = {"status": "approved"}
    if system_user:
        defaults["created_by"] = system_user

    obj, created = Model.objects.get_or_create(defaults=defaults, **lookup)

    if created:
        # Force approved directly so the post_save signal does NOT
        # add a redundant approval-queue entry.
        Model.objects.filter(pk=obj.pk).update(status="approved")
        obj.status = "approved"

    return obj, created


def _extract_qa_blocks(lines: list) -> list:
    """
    Splits a list of lines into Q&A sections.
    Returns list of {"question": str, "bullets": [str], "answer_text": str}
    """
    q_pattern = re.compile(
        r'^\s*(?:Q\s*\d+[\.\):]?|Question\s*\d+[\.\):]?|\d+[\.\)])\s+(.+)',
        re.IGNORECASE
    )
    bullet_pattern = re.compile(r'^\s*[·•\-\*]\s*(.+)')
    answer_start   = re.compile(r'^\s*Answer\s*[:\-]?\s*$', re.IGNORECASE)

    sections = []
    current_q = None
    in_answer = False
    plain_answer_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        m = q_pattern.match(line)
        if m:
            # Save previous
            if current_q is not None:
                current_q["answer_text"] = " ".join(plain_answer_lines).strip()
                sections.append(current_q)
            current_q = {"question": m.group(1).strip(), "bullets": []}
            in_answer = False
            plain_answer_lines = []
            continue

        if current_q is None:
            continue

        if answer_start.match(line):
            in_answer = True
            continue

        if in_answer:
            bm = bullet_pattern.match(line)
            if bm:
                current_q["bullets"].append(bm.group(1).strip())
            else:
                plain_answer_lines.append(stripped)

    # Flush last
    if current_q is not None:
        current_q["answer_text"] = " ".join(plain_answer_lines).strip()
        sections.append(current_q)

    return sections


# ──────────────────────────────────────────────────────────────────────────────
# FLAT / FALLBACK PARSERS
# ──────────────────────────────────────────────────────────────────────────────

def _parse_flat(text: str) -> list:
    """Tries explicit Q:/A:, then numbered, then paragraph pairs."""
    for strategy in (_strategy_explicit_qa, _strategy_numbered, _strategy_paragraph_pairs):
        result = strategy(text)
        if result:
            return result
    return []


def _strategy_explicit_qa(text: str) -> list:
    q_splits = re.split(
        r'\n?\s*(?:Q\s*[\.:]\s*|Question\s*[\.:]\s*)',
        text, flags=re.IGNORECASE
    )
    sections = []
    for chunk in q_splits[1:]:
        a_split = re.split(
            r'\n?\s*(?:A\s*[\.:]\s*|Answer\s*[\.:]\s*)',
            chunk, maxsplit=1, flags=re.IGNORECASE
        )
        q_text = re.sub(r'\s*(?:Q\s*[\.:]).*$', '', a_split[0].strip(),
                        flags=re.IGNORECASE | re.DOTALL).strip()
        a_text = re.sub(r'\s*(?:Q\s*[\.:]).*$', '',
                        a_split[1].strip() if len(a_split) > 1 else "",
                        flags=re.IGNORECASE | re.DOTALL).strip()
        if len(q_text) >= 10 and len(a_text) >= 5:
            sections.append({"question": q_text, "bullets": [], "answer_text": a_text})
    return sections[:200]


def _strategy_numbered(text: str) -> list:
    lines = [ln.rstrip() for ln in text.split("\n")]
    sections = []
    i = 0
    while i < len(lines):
        m = re.match(r'^(\d+)[\.\)]\s+(.{10,})', lines[i])
        if m:
            q_text = m.group(2).strip()
            answer_lines = []
            j = i + 1
            while j < len(lines):
                nl = lines[j].strip()
                if re.match(r'^\d+[\.\)]\s+', nl):
                    break
                if nl:
                    answer_lines.append(nl)
                elif answer_lines:
                    break
                j += 1
            a_text = " ".join(answer_lines).strip()
            if len(a_text) >= 5:
                sections.append({"question": q_text, "bullets": [], "answer_text": a_text})
            i = j
        else:
            i += 1
    return sections[:200]


def _strategy_paragraph_pairs(text: str) -> list:
    paragraphs = [
        p.strip() for p in re.split(r'\n{2,}', text)
        if p.strip() and len(p.strip()) > 10
    ]
    sections = []
    for i in range(0, len(paragraphs) - 1, 2):
        q, a = paragraphs[i], paragraphs[i + 1]
        if len(q) >= 10 and len(a) >= 5:
            sections.append({"question": q, "bullets": [], "answer_text": a})
    return sections[:100]


# ──────────────────────────────────────────────────────────────────────────────
# SAVE SECTION  (Question + Answer + AnswerPoints)
# ──────────────────────────────────────────────────────────────────────────────

def _save_section(section: dict, user, subcategory, report: dict):
    """
    Save one Q&A section.

    section keys:
      question     – question title string
      bullets      – list of bullet-point strings (may be empty)
      answer_text  – plain prose answer (may be empty string)
    """
    from apps.core.models import Question, Answer, AnswerPoint
    from apps.core.services.duplicate_detector import normalize_question, find_similar_questions

    title = section["question"].strip()
    if not title:
        return

    # Duplicate detection
    dupes = find_similar_questions(title, threshold=88)
    if dupes:
        report["duplicates_skipped"] += 1
        return

    with transaction.atomic():
        question = Question.objects.create(
            subcategory=subcategory,
            title=title,
            normalized_title=normalize_question(title),
            created_by=user,
        )
        report["questions_created"] += 1

        bullets    = section.get("bullets", [])
        plain_text = section.get("answer_text", "").strip()

        # Decide how to build the answer
        if bullets:
            # Store each bullet as an AnswerPoint; plain text (if any) goes into Answer.content
            answer_content = plain_text if plain_text else "See answer points below."
            answer = Answer.objects.create(
                question=question,
                content=answer_content,
                created_by=user,
            )
            report["answers_created"] += 1

            for bullet in bullets:
                if bullet.strip():
                    AnswerPoint.objects.create(
                        answer=answer,
                        point=bullet.strip(),
                        created_by=user,
                    )
                    report["answer_points_created"] += 1

        elif plain_text:
            Answer.objects.create(
                question=question,
                content=plain_text,
                created_by=user,
            )
            report["answers_created"] += 1


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _get_or_create_pdf_subcategory(user):
    """Fallback subcategory when no structured headers are found."""
    from apps.core.models import Topic, Category, SubCategory
    topic, _ = _get_or_create_approved(Topic, {"name": "PDF Imports"})
    category, _ = _get_or_create_approved(Category, {"topic": topic, "name": "Imported Content"})
    subcat, _ = _get_or_create_approved(SubCategory, {"category": category, "name": "PDF Extracted"})
    return subcat


def _format_report(report: dict) -> str:
    lines = [
        f"Topics/Categories/Subcategories created: "
        f"{report.get('topics_created',0)} / {report.get('categories_created',0)} / {report.get('subcategories_created',0)}",
        f"Questions created:    {report['questions_created']}",
        f"Answers created:      {report['answers_created']}",
        f"Answer points added:  {report.get('answer_points_created', 0)}",
        f"Duplicates skipped:   {report['duplicates_skipped']}",
    ]
    if report.get("errors"):
        lines.append(f"Errors ({len(report['errors'])}):")
        for e in report["errors"][:10]:
            lines.append(f"  • {e}")
    return "\n".join(lines)
