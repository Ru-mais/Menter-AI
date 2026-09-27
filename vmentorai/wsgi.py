"""
WSGI config for vmentorai project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application


# Load .env file
try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmentorai.settings')

# Run migrations automatically if on Vercel
if os.environ.get('VERCEL') == '1':
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'migrate'])
    except Exception as e:
        print(f"Failed to run migrations on Vercel startup: {e}")

application = get_wsgi_application()
