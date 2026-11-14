"""Excepciones propias del módulo de visión."""


class ErrorVision(Exception):
    """Error base del módulo de visión. Todas las demás heredan de esta."""


class ImagenInvalidaError(ErrorVision):
    """La imagen recibida está vacía, dañada o no se puede decodificar."""


class ModelosNoDisponiblesError(ErrorVision):
    """Faltan los archivos de los modelos o no se pudieron cargar."""
