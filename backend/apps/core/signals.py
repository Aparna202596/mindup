from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import Topic, Category, SubCategory, Answer, AnswerPoint, Question


@receiver(post_save, sender=Question)
def question_post_save(sender, instance, created, **kwargs):
    """Update search vector whenever a question is saved."""
    from django.contrib.postgres.search import SearchVector
    Question.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector("title", "normalized_title", config="english")
    )


@receiver(post_save, sender=Topic)
def topic_post_save(sender, instance, created, **kwargs):
    if not created or not instance.created_by_id:
        return
    from apps.core.services.approval_service import create_approval_request
    from apps.core.services.audit_service import create_audit_log
    create_approval_request(object_type="topic", object_id=instance.id, user=instance.created_by)
    create_audit_log(user=instance.created_by, action="CREATE", object_type="Topic",
                     object_id=instance.id, new_data={"name": instance.name})


@receiver(post_save, sender=Category)
def category_post_save(sender, instance, created, **kwargs):
    if not created or not instance.created_by_id:
        return
    from apps.core.services.approval_service import create_approval_request
    create_approval_request(object_type="category", object_id=instance.id, user=instance.created_by)


@receiver(post_save, sender=SubCategory)
def subcategory_post_save(sender, instance, created, **kwargs):
    if not created or not instance.created_by_id:
        return
    from apps.core.services.approval_service import create_approval_request
    create_approval_request(object_type="subcategory", object_id=instance.id, user=instance.created_by)


@receiver(post_save, sender=Answer)
def answer_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.core.services.notification_service import create_notification
    if (instance.question.created_by_id and
            instance.question.created_by_id != instance.created_by_id):
        create_notification(
            user=instance.question.created_by,
            title="New Answer",
            message=f'Your question "{instance.question.title[:50]}" received a new answer.',
        )


@receiver(post_save, sender=AnswerPoint)
def answer_point_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.core.services.notification_service import create_notification
    if (instance.answer.created_by_id and
            instance.answer.created_by_id != instance.created_by_id):
        create_notification(
            user=instance.answer.created_by,
            title="New Answer Point",
            message="A new key point was added to your answer.",
        )