from django.db.models.signals import post_save

from django.dispatch import receiver

from apps.topics.models import Topic

@receiver(post_save, sender=Topic)
def topic_created(sender, instance, created, **kwargs):

    if created:

        from apps.core.services.audit_service import (
            create_audit_log
        )

        create_audit_log(
            user=instance.created_by,
            action="CREATE",
            object_type="Topic",
            object_id=instance.id,
            new_data={
                "name": instance.name
            }
        )