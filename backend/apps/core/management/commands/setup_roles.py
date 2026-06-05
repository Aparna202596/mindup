from django.core.management.base import BaseCommand
from apps.core.models import Role, CustomUser


class Command(BaseCommand):
    help = "Create default roles and assign Admin to all superusers"

    def handle(self, *args, **kwargs):
        admin_role, created = Role.objects.get_or_create(name="Admin")
        Role.objects.get_or_create(name="User")

        if created:
            self.stdout.write(self.style.SUCCESS("Created Admin role"))

        count = 0
        for user in CustomUser.objects.filter(is_superuser=True):
            if user.role != admin_role:
                user.role = admin_role
                user.save()
                count += 1
                self.stdout.write(f"  Assigned Admin to: {user.email}")

        self.stdout.write(self.style.SUCCESS(f"Done. {count} user(s) updated."))