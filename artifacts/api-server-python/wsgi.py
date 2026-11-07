#!/usr/bin/env python
"""Production WSGI entry point for the Django application."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
application = get_wsgi_application()
app = application  # Keep existing Gunicorn commands using wsgi:app working.
