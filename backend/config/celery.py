import os
from celery import Celery
import django

# 1. Set the default Django settings module environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Force Django setup to populate settings
django.setup()

# 2. Instantiate our core worker engine instance
app = Celery('mindup')

# 3. Pull task routing configurations directly out of your settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4. Automatically detect and load tasks dynamically from your apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')