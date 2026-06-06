import os
import re
from apps.core.models import PDFUpload, Answer
from apps.core.services.duplicate_detector import normalize_question


def process_pdf(upload_id: str) -> dict:
    try:
        upload = PDFUpload.objects.get(id=upload_id)
    except PDFUpload.DoesNotExist:
        return {"error": "Upload not found"}

    upload.process_status = "processing"
    upload.save(update_fields=["process_status"])

    report = {
        "questions_created": 0,
        "answers_created": 0,
        "duplicates_skipped": 0,
        "errors": [],
    }

    try:
        text = _extract_text(upload.file.path)
        if not text.strip():
            raise ValueError("No readable text found in PDF.")

        sections = _parse_sections(text)
        if not sections:
            raise ValueError(
                "Could not detect Q&A structure. "
                "Use 'Q:' / 'A:' or numbered questions in your PDF."
            )

        user = upload.uploaded_by
        subcategory = _get_or_create_pdf_subcategory(user)

        for section in sections:
            try:
                _save_section(section, user, subcategory, report)
            except Exception as e:
                report["errors"].append(str(e))

        upload.process_status = "completed"
        upload.processing_report = _format_report(report)

    except Exception as e:
        upload.process_status = "failed"
        upload.processing_report = f"Processing failed: {str(e)}"

    upload.save(update_fields=["process_status", "processing_report"])
    return report


def _extract_text(file_path: str) -> str:
    try:
        import pypdf
        parts = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts)
    except ImportError:
        raise ValueError("pypdf not installed. Run: pip install pypdf")
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e}")


def _parse_sections(text: str) -> list:
    """
    Three strategies tried in order.
    Returns list of {"question": str, "answer": str}
    """
    sections = _strategy_explicit_qa(text)
    if sections:
        return sections

    sections = _strategy_numbered(text)
    if sections:
        return sections

    sections = _strategy_paragraph_pairs(text)
    return sections


def _strategy_explicit_qa(text: str) -> list:
    """
    Matches explicit Q:/A: or Question:/Answer: markers.
    Works even when question or answer spans multiple lines.
    """
    # Split on Q: or Question: markers first
    q_splits = re.split(
        r'\n?\s*(?:Q\s*[\.:]\s*|Question\s*[\.:]\s*)',
        text, flags=re.IGNORECASE
    )
    sections = []
    for chunk in q_splits[1:]:   # skip text before first Q:
        # Now split this chunk on A: or Answer:
        a_split = re.split(
            r'\n?\s*(?:A\s*[\.:]\s*|Answer\s*[\.:]\s*)',
            chunk, maxsplit=1, flags=re.IGNORECASE
        )
        question_text = a_split[0].strip()
        answer_text = a_split[1].strip() if len(a_split) > 1 else ""

        # Clean trailing Q: that bleeds in
        question_text = re.sub(
            r'\s*(?:Q\s*[\.:]).*$', '', question_text,
            flags=re.IGNORECASE | re.DOTALL
        ).strip()
        answer_text = re.sub(
            r'\s*(?:Q\s*[\.:]).*$', '', answer_text,
            flags=re.IGNORECASE | re.DOTALL
        ).strip()

        if len(question_text) >= 10 and len(answer_text) >= 5:
            sections.append({"question": question_text, "answer": answer_text})

    return sections[:200]


def _strategy_numbered(text: str) -> list:
    """
    Matches numbered patterns like:
      1. Question text
         Answer text (next non-empty line or block)
    """
    lines = [l.rstrip() for l in text.split('\n')]
    sections = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\d+)[\.\)]\s+(.{10,})', line)
        if m:
            question_text = m.group(2).strip()
            # Collect answer lines until next numbered item or blank gap
            answer_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if re.match(r'^\d+[\.\)]\s+', next_line):
                    break
                if next_line:
                    answer_lines.append(next_line)
                elif answer_lines:
                    break   # blank line after content = end of answer
                j += 1
            answer_text = " ".join(answer_lines).strip()
            if len(answer_text) >= 5:
                sections.append({"question": question_text, "answer": answer_text})
            i = j
        else:
            i += 1
    return sections[:200]


def _strategy_paragraph_pairs(text: str) -> list:
    """
    Last resort: treat alternating non-empty paragraphs as Q then A.
    Only used when nothing else matches.
    """
    paragraphs = [
        p.strip() for p in re.split(r'\n{2,}', text)
        if p.strip() and len(p.strip()) > 10
    ]
    sections = []
    for i in range(0, len(paragraphs) - 1, 2):
        q = paragraphs[i]
        a = paragraphs[i + 1]
        if len(q) >= 10 and len(a) >= 5:
            sections.append({"question": q, "answer": a})
    return sections[:100]


def _save_section(section: dict, user, subcategory, report: dict):
    from apps.core.models import Question, Answer
    from apps.core.services.duplicate_detector import normalize_question, find_similar_questions

    title = section["question"]
    dupes = find_similar_questions(title, threshold=90)  # stricter = fewer false positives
    if dupes:
        report["duplicates_skipped"] += 1
        return

    question = Question.objects.create(
        subcategory=subcategory,
        title=title,
        normalized_title=normalize_question(title),
        created_by=user,
    )
    report["questions_created"] += 1

    answer_text = section.get("answer", "").strip()
    if answer_text:
        Answer.objects.create(
            question=question,
            content=answer_text,
            created_by=user,
        )
        report["answers_created"] += 1


def _get_or_create_pdf_subcategory(user):
    from apps.core.models import Topic, Category, SubCategory
    topic, _ = Topic.objects.get_or_create(
        name="PDF Imports",
        defaults={"created_by": user, "status": "approved"},
    )
    category, _ = Category.objects.get_or_create(
        topic=topic,
        name="Imported Content",
        defaults={"created_by": user, "status": "approved"},
    )
    subcategory, _ = SubCategory.objects.get_or_create(
        category=category,
        name="PDF Extracted",
        defaults={"created_by": user, "status": "approved"},
    )
    return subcategory


def _format_report(report: dict) -> str:
    lines = [
        f"Questions created:   {report['questions_created']}",
        f"Answers created:     {report['answers_created']}",
        f"Duplicates skipped:  {report['duplicates_skipped']}",
    ]
    if report.get("errors"):
        lines.append(f"Errors ({len(report['errors'])}):")
        for e in report["errors"][:10]:
            lines.append(f"  • {e}")
    return "\n".join(lines)