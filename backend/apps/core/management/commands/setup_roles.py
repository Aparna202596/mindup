from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.core.models import Question, CustomUser

def handle(self, *args, **options):
    ct = ContentType.objects.get_for_model(Question)
    bulk_perm, _ = Permission.objects.get_or_create(
        codename="bulk_upload_question",
        content_type=ct,
        defaults={"name": "Can perform bulk Q&A upload"}
    )
    # Assign to all staff users
    for user in CustomUser.objects.filter(is_staff=True, is_superuser=False):
        user.user_permissions.add(bulk_perm)