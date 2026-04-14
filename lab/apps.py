import os
import sys

from django.apps import AppConfig
from django.conf import settings


class LabConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lab'

    def ready(self):
        if 'runserver' not in sys.argv:
            return
        if settings.DEBUG and os.environ.get('RUN_MAIN') != 'true':
            return
        try:
            from .services.model_catalog import refresh_model_catalog

            refresh_model_catalog()
        except Exception:
            pass
