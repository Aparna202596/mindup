from .celery import app as celery_app

# This guarantees that the app is loaded when Django starts
__all__ = ('celery_app',)