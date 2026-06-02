from django.db.models.signals import post_save

from django.dispatch import receiver

from apps.topics.models import Topic

@receiver(post_save, sender=Topic)
def topic_approval_creation(
        sender,
        instance,
        created,
        **kwargs
):

    if created:

        from apps.approvals.services.approval_service import (
            create_approval_request
        )

        create_approval_request(
            object_type="topic",
            object_id=instance.id,
            user=instance.created_by
        )