"""Configuración WSGI del proyecto EmoSense.

Expone la variable ``application`` usada por servidores WSGI.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emosense.settings")

application = get_wsgi_application()
