"""
Módulo de visión artificial de EmoSense (solo OpenCV).

Uso principal::

    from detector.vision import analizar_imagen
    resultado = analizar_imagen(bytes_jpeg)

Las imágenes se procesan únicamente en memoria; nunca se guardan.
"""

from .analizador import analizar_imagen
from .errores import ErrorVision, ImagenInvalidaError, ModelosNoDisponiblesError

__all__ = [
    "analizar_imagen",
    "ErrorVision",
    "ImagenInvalidaError",
    "ModelosNoDisponiblesError",
]
