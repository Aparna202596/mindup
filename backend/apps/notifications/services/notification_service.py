from apps.notifications.models import Notification

def create_notification(*, user, title, message):

    Notification.objects.create(
        user=user,
        title=title,
        message=message
    )
    create_notification(
        user=user,
        title="Topic Approved",
        message="Your topic has been approved."
    )