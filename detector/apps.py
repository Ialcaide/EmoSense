"""Configuración de la app 'detector'."""

from django.apps import AppConfig


class DetectorConfig(AppConfig):
    """Registro de la app detector: detección de rostros y estimación de expresiones."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "detector"
    verbose_name = "Detector"
