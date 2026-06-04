import os
import re
from apps.core.models import PDFUpload, Topic, Category, SubCategory, Question, Answer
from apps.core.services.question_service import create_question
from apps.core.services.duplicate_detector import normalize_question


def process_pdf(upload_id: str) -> dict:
    """
    Extract text from a PDF and auto-create topics/questions/answers.
    Called after upload. Returns a processing report dict.
    """
    try:
        upload = PDFUpload.objects.get(id=upload_id)
    except PDFUpload.DoesNotExist:
        return {"error": "Upload not found"}

    upload.process_status = "processing"
    upload.save(update_fields=["process_status"])

    report = {
        "topics_created": 0,
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
        user = upload.uploaded_by

        for section in sections:
            try:
                _create_content(section, user, report)
            except Exception as e:
                report["errors"].append(str(e))

        upload.process_status = "completed"
        upload.processing_report = _format_report(report)

    except Exception as e:
        upload.process_status = "failed"
        upload.processing_report = f"Processing failed: {str(e)}"
        report["errors"].append(str(e))

    upload.save(update_fields=["process_status", "processing_report"])
    return report


def _extract_text(file_path: str) -> str:
    try:
        import pypdf
        text_parts = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except ImportError:
        raise ValueError("pypdf is not installed. Run: pip install pypdf")
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e}")


def _parse_sections(text: str) -> list:
    """
    Parse PDF text into structured sections.
    Looks for patterns like:
      Q: ... or Question: ...
      A: ... or Answer: ...
    Returns list of dicts with keys: question, answer
    """
    sections = []

    # Strategy 1: Q/A pattern
    qa_pattern = re.findall(
        r'(?:Q[:\.]?\s*|Question[:\s]+)(.*?)(?=(?:A[:\.]?\s*|Answer[:\s]+))(.*?)(?=(?:Q[:\.]?\s*|Question[:\s]+)|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    for match in qa_pattern:
        question_text = match[0].strip()
        answer_text = re.sub(r'^(?:A[:\.]?\s*|Answer[:\s]+)', '', match[1], flags=re.IGNORECASE).strip()
        if len(question_text) > 10 and len(answer_text) > 20:
            sections.append({"question": question_text, "answer": answer_text})

    # Strategy 2: Numbered lines if Q/A pattern found nothing
    if not sections:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        i = 0
        while i < len(lines) - 1:
            line = lines[i]
            next_line = lines[i + 1]
            if re.match(r'^\d+[\.\)]\s+.{10,}', line) and len(next_line) > 20:
                question_text = re.sub(r'^\d+[\.\)]\s+', '', line)
                sections.append({"question": question_text, "answer": next_line})
                i += 2
            else:
                i += 1

    return sections[:50]  # cap at 50 per upload


def _create_content(section: dict, user, report: dict):
    from apps.core.models import SubCategory

    # Find or use a default subcategory for PDF-imported content
    subcategory = _get_or_create_pdf_subcategory(user)
    if not subcategory:
        report["errors"].append("Could not find a subcategory for PDF content.")
        return

    result = create_question(
        user=user,
        subcategory=subcategory,
        title=section["question"],
    )

    if not result["success"]:
        report["duplicates_skipped"] += 1
        return

    question = result["question"]
    report["questions_created"] += 1

    Answer.objects.create(
        question=question,
        content=section["answer"],
        created_by=user,
    )
    report["answers_created"] += 1


def _get_or_create_pdf_subcategory(user):
    """Get or create the default PDF Import subcategory."""
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
        f"Questions created: {report['questions_created']}",
        f"Answers created:   {report['answers_created']}",
        f"Duplicates skipped: {report['duplicates_skipped']}",
    ]
    if report["errors"]:
        lines.append(f"Errors: {len(report['errors'])}")
        for e in report["errors"][:5]:
            lines.append(f"  - {e}")
    return "\n".join(lines)