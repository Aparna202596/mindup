from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_pdf_task(self, upload_id: str):
    """
    Async Celery task for PDF processing.
    Retries up to 3 times on failure with 60s delay.
    """
    try:
        logger.info(f"Starting PDF processing for upload: {upload_id}")
        from apps.core.services.pdf_processor import process_pdf
        report = process_pdf(upload_id)
        logger.info(f"PDF processing complete for {upload_id}: {report}")
        return report
    except Exception as exc:
        logger.error(f"PDF processing failed for {upload_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def send_notification_task(user_id: str, title: str, message: str):
    """Async notification delivery."""
    try:
        from apps.core.models import CustomUser
        from apps.core.services.notification_service import create_notification
        user = CustomUser.objects.get(id=user_id)
        create_notification(user=user, title=title, message=message)
        logger.info(f"Notification sent to {user.email}: {title}")
    except Exception as e:
        logger.error(f"Notification failed: {e}")


@shared_task
def cleanup_old_notifications_task():
    """
    Periodic task: delete read notifications older than 30 days.
    Run via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.core.models import Notification
    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = Notification.objects.filter(is_read=True, created_at__lt=cutoff).delete()
    logger.info(f"Cleaned up {deleted} old notifications")
    return deleted


@shared_task
def update_search_vectors_task():
    """
    Periodic task: rebuild PostgreSQL search vectors for all questions.
    """
    from django.contrib.postgres.search import SearchVector
    from apps.core.models import Question
    Question.objects.update(
        search_vector=SearchVector('title', 'normalized_title')
    )
    count = Question.objects.count()
    logger.info(f"Updated search vectors for {count} questions")
    return count