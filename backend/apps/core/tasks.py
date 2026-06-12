from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_notification_task(user_id: str, title: str, message: str):
    """Async notification delivery."""
    try:
        from apps.core.models import CustomUser
        from apps.core.services.notification_service import create_notification
        user = CustomUser.objects.get(id=user_id)
        create_notification(user=user, title=title, message=message)
        logger.info("Notification sent to %s: %s", user.email, title)
    except Exception as exc:
        logger.error("Notification failed: %s", exc)


@shared_task
def cleanup_old_notifications_task():
    """Periodic: delete read notifications older than 30 days."""
    from django.utils    import timezone
    from datetime        import timedelta
    from apps.core.models import Notification

    cutoff   = timezone.now() - timedelta(days=30)
    deleted, _ = Notification.objects.filter(
        is_read=True, created_at__lt=cutoff
    ).delete()
    logger.info("Cleaned up %d old notifications", deleted)
    return deleted


@shared_task
def update_search_vectors_task():
    """Periodic: rebuild PostgreSQL search vectors for all questions."""
    from django.contrib.postgres.search import SearchVector
    from apps.core.models import Question

    updated = Question.objects.update(
        search_vector=SearchVector("title", "normalized_title", config="english")
    )
    logger.info("Updated search vectors for %d questions", updated)
    return updated