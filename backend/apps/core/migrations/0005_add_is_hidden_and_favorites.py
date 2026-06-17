from django.db import migrations, models
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_question_options_answer_updated_by_and_more'),
    ]

    operations = [
        # Add is_hidden to Topic
        migrations.AddField(
            model_name='topic',
            name='is_hidden',
            field=models.BooleanField(default=False),
        ),
        # Add is_hidden to Category
        migrations.AddField(
            model_name='category',
            name='is_hidden',
            field=models.BooleanField(default=False),
        ),
        # Add is_hidden to SubCategory
        migrations.AddField(
            model_name='subcategory',
            name='is_hidden',
            field=models.BooleanField(default=False),
        ),
        # Add is_hidden to Question
        migrations.AddField(
            model_name='question',
            name='is_hidden',
            field=models.BooleanField(default=False),
        ),
        # Create Favorite model
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_type', models.CharField(
                    choices=[
                        ('topic', 'Topic'),
                        ('category', 'Category'),
                        ('subcategory', 'SubCategory'),
                        ('question', 'Question'),
                    ],
                    max_length=20,
                )),
                ('object_id', models.UUIDField()),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='favorites',
                    to='core.customuser',
                )),
            ],
            options={
                'unique_together': {('user', 'content_type', 'object_id')},
            },
        ),
    ]
