"""Configuración ASGI del proyecto EmoSense.

Expone la variable ``application`` usada por servidores ASGI.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emosense.settings")

application = get_asgi_application()
