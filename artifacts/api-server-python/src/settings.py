"""Settings for the stateless sales API and dashboard."""

import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / 'sales-ai'
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or get_random_secret_key()
DEBUG = os.getenv('APP_ENV', os.getenv('NODE_ENV', 'production')).lower() != 'production'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
ALLOWED_HOSTS.extend(host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if host.strip())
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])

ROOT_URLCONF = 'src.urls'
WSGI_APPLICATION = 'wsgi.application'
APPEND_SLASH = False

INSTALLED_APPS = ['corsheaders']
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
]
CORS_ALLOW_ALL_ORIGINS = True
