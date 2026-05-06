"""PythonAnywhere WSGI entry point."""
import os
import sys

# Add project root to Python path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# ============ Production settings for PythonAnywhere ============
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoblog.settings')
os.environ.setdefault('DJANGO_DEBUG', 'False')
os.environ.setdefault('COMPRESS_ENABLED', 'False')

# IMPORTANT: Replace with your actual PythonAnywhere domain
# e.g., 'yourusername.pythonanywhere.com'
os.environ.setdefault('ALLOWED_HOSTS', '.pythonanywhere.com,localhost')
os.environ.setdefault(
    'CSRF_TRUSTED_ORIGINS',
    'https://*.pythonanywhere.com,http://*.pythonanywhere.com'
)

# Generate a strong secret key once and keep it here
# You can generate one using: python -c "import secrets; print(secrets.token_urlsafe(50))"
os.environ.setdefault(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-this-to-a-real-secret-key-in-production'
)

# Disable Redis (use local memory cache instead on PA)
if 'DJANGO_REDIS_URL' in os.environ:
    del os.environ['DJANGO_REDIS_URL']

# ============ WSGI Application ============
from djangoblog.wsgi import application
