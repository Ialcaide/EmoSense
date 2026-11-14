"""Modelos de la app 'detector'. Solo guardan resultados anónimos (sin imágenes)."""

from django.db import models

from .emociones_info import EMOCIONES


class Analisis(models.Model):
    """Resultado anónimo de un análisis de expresión facial.

    No guarda imágenes, rostros ni datos personales: solo la expresión
    estimada, sus puntuaciones y datos técnicos del procesamiento.
    """

    class Fuente(models.TextChoices):
        """Origen de la imagen analizada."""

        CAMARA = "camara", "Cámara"
        FOTO = "foto", "Foto"

    fuente = models.CharField("fuente", max_length=10, choices=Fuente.choices)
    cantidad_rostros = models.PositiveSmallIntegerField("cantidad de rostros", default=0)
    emocion_principal = models.CharField(
        "emoción principal",
        max_length=10,
        blank=True,
        choices=[(clave, datos["nombre"]) for clave, datos in EMOCIONES.items()],
        help_text="Vacío si no se detectó ningún rostro.",
    )
    puntuacion = models.FloatField("puntuación", null=True, blank=True)
    puntuaciones = models.JSONField(
        "puntuaciones",
        default=list,
        blank=True,
        help_text="Lista [{emocion, puntuacion}] del rostro principal.",
    )
    tiempo_ms = models.FloatField("tiempo de proceso (ms)", default=0)
    fecha = models.DateTimeField("fecha", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "análisis"
        verbose_name_plural = "análisis"
        ordering = ["-fecha"]

    def __str__(self):
        """Texto legible, p. ej. 'Cámara · Alegría (0.92)'."""
        if not self.emocion_principal:
            return f"{self.get_fuente_display()} · sin rostro"
        return f"{self.get_fuente_display()} · {self.get_emocion_principal_display()} ({self.puntuacion:.2f})"


class SesionPractica(models.Model):
    """Resultado anónimo de una sesión del medidor de amabilidad.

    Solo guarda la duración, el porcentaje de análisis con expresión amable
    (alegría o neutral) y cuántos análisis con rostro hubo. Sin imágenes.
    """

    duracion = models.PositiveSmallIntegerField("duración (s)")
    porcentaje_amable = models.FloatField("porcentaje amable")
    cantidad_analisis = models.PositiveIntegerField("cantidad de análisis")
    fecha = models.DateTimeField("fecha", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "sesión de práctica"
        verbose_name_plural = "sesiones de práctica"
        ordering = ["-fecha"]

    def __str__(self):
        """Texto legible, p. ej. 'Sesión de 60 s · 85.0 % amable'."""
        return f"Sesión de {self.duracion} s · {self.porcentaje_amable:.1f} % amable"
