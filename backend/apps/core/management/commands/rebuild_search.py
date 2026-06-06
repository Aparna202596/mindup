from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from apps.core.models import Question


class Command(BaseCommand):
    help = "Rebuild PostgreSQL full-text search vectors for all questions"

    def handle(self, *args, **kwargs):
        self.stdout.write("Rebuilding search vectors...")
        count = Question.objects.update(
            search_vector=SearchVector("title", "normalized_title", config="english")
        )
        self.stdout.write(self.style.SUCCESS(f"Updated {count} questions."))