from django.db import migrations
from django.contrib.postgres.operations import CreateExtension


class Migration(migrations.Migration):
    # This prevents Django from wrapping everything in a transaction block 👇
    atomic = False

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        # Enable pg_trgm for trigram similarity search
        CreateExtension("pg_trgm"),

        # GIN index on search_vector for full-text search
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    question_search_vector_gin
                ON core_question
                USING gin(search_vector);
            """,
            reverse_sql="DROP INDEX IF EXISTS question_search_vector_gin;",
        ),

        # Trigram index on title for fast LIKE/ILIKE queries
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    question_title_trgm
                ON core_question
                USING gin(title gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX IF EXISTS question_title_trgm;",
        ),

        # Trigram index on topic names
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    topic_name_trgm
                ON core_topic
                USING gin(name gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX IF EXISTS topic_name_trgm;",
        ),
    ]