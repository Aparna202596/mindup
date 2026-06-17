"""
Migration 0006 — Enable PostgreSQL pg_trgm extension

Run AFTER 0005_add_is_hidden_and_favorites.
Required for trigram fuzzy-search in duplicate_detector.py.

Apply with:
    python manage.py migrate
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_add_is_hidden_and_favorites'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
    ]
