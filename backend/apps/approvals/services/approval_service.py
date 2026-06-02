from apps.approvals.models import ApprovalQueue

def create_approval_request(
        *,
        object_type,
        object_id,
        user
):

    ApprovalQueue.objects.create(
        object_type=object_type,
        object_id=object_id,
        requested_by=user
    )