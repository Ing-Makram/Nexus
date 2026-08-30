#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

from dotenv import load_dotenv


def main():
    """Run administrative tasks."""
    # Load environment variables from the root .env file if it exists,
    # or look for a .env file locally in the backend folder.
    root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    local_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    if os.path.exists(root_env):
        load_dotenv(root_env)
    elif os.path.exists(local_env):
        load_dotenv(local_env)

    # Default to development settings if ENVIRONMENT or DJANGO_SETTINGS_MODULE isn't explicitly defined.
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        if environment == "production":
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
        else:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
