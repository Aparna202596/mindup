from apps.core.models import AuditLog

def create_audit_log(
        *,
        user,
        action,
        object_type,
        object_id,
        old_data=None,
        new_data=None
):

    AuditLog.objects.create(
        user=user,
        action=action,
        object_type=object_type,
        object_id=object_id,
        previous_data=old_data,
        new_data=new_data
    )