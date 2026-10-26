import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bakam_zone.settings')
app = Celery('bakam_zone')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
import bakam_zone.tasks