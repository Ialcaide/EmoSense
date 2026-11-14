"""Registro de modelos de 'detector' en el panel de administración."""

from django.contrib import admin

from .amabilidad import nivel_por_porcentaje
from .models import Analisis, SesionPractica


class SoloLecturaAdmin(admin.ModelAdmin):
    """Base de solo lectura: los registros los crea la API."""

    def has_add_permission(self, request):
        """Los registros solo se crean desde la API."""
        return False

    def has_change_permission(self, request, obj=None):
        """Los resultados no se editan para no alterar las estadísticas."""
        return False


@admin.register(Analisis)
class AnalisisAdmin(SoloLecturaAdmin):
    """Consulta de análisis anónimos."""

    list_display = ("fecha", "fuente", "emocion_principal", "puntuacion", "cantidad_rostros", "tiempo_ms")
    list_filter = ("fuente", "emocion_principal", "cantidad_rostros", "fecha")
    date_hierarchy = "fecha"
    ordering = ("-fecha",)
    list_per_page = 50


@admin.register(SesionPractica)
class SesionPracticaAdmin(SoloLecturaAdmin):
    """Consulta de sesiones anónimas del medidor de amabilidad."""

    list_display = ("fecha", "duracion", "porcentaje_amable", "nivel", "cantidad_analisis")
    list_filter = ("fecha",)
    date_hierarchy = "fecha"
    ordering = ("-fecha",)
    list_per_page = 50

    @admin.display(description="nivel")
    def nivel(self, obj):
        """Nivel según los umbrales del medidor (excelente, bueno, mejorar)."""
        return nivel_por_porcentaje(obj.porcentaje_amable)
