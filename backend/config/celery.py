import os

from celery import Celery

from config.settings import resolve_settings_module

# Set the default Django settings module for the 'celery' program.
# Respects DJANGO_SETTINGS_MODULE / ENVIRONMENT the same way manage.py does.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", resolve_settings_module())

app = Celery("nexus")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
