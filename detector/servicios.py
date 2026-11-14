"""
Lógica de la API de análisis: validación de la imagen y registro anónimo.

Las imágenes solo se leen en memoria; nunca se guardan en disco ni en la
base de datos.
"""

import time

from django.conf import settings

from .models import Analisis

# Intervalo mínimo entre registros de cámara por sesión (segundos).
INTERVALO_REGISTRO_CAMARA = 5
CLAVE_SESION_CAMARA = "ultimo_registro_camara"

# Firmas (bytes iniciales) de los formatos permitidos para fotos.
FIRMAS = {
    "jpg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
}


class ErrorSolicitud(Exception):
    """Error de validación que se devuelve al cliente como JSON."""

    def __init__(self, codigo, mensaje, estado=400):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.estado = estado


def detectar_formato(datos):
    """Identifica el formato real por su firma: 'jpg', 'png', 'webp' o None."""
    for formato, firmas in FIRMAS.items():
        if datos.startswith(firmas):
            return formato
    if len(datos) >= 12 and datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "webp"
    return None


def leer_imagen(request, validar_formato=False):
    """Obtiene y valida los bytes del campo 'imagen' de una petición multipart.

    Args:
        request: petición de Django.
        validar_formato: si es True, solo acepta JPG, PNG o WebP (fotos).

    Returns:
        bytes de la imagen (solo en memoria).

    Raises:
        ErrorSolicitud: con código ``muy_grande``, ``sin_imagen`` o ``formato``.
    """
    limite = settings.TAMANO_MAX_IMAGEN
    mensaje_grande = f"La imagen supera el máximo de {limite // (1024 * 1024)} MB."

    # Se revisa el tamaño de la petición antes de leer el cuerpo.
    try:
        longitud = int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        longitud = 0
    if longitud > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
        raise ErrorSolicitud("muy_grande", mensaje_grande, 413)

    archivo = request.FILES.get("imagen")
    if archivo is None:
        raise ErrorSolicitud("sin_imagen", "No se recibió ninguna imagen en el campo 'imagen'.")
    if archivo.size == 0:
        raise ErrorSolicitud("sin_imagen", "La imagen recibida está vacía.")
    if archivo.size > limite:
        raise ErrorSolicitud("muy_grande", mensaje_grande, 413)

    datos = archivo.read()
    archivo.close()

    if validar_formato and detectar_formato(datos) is None:
        raise ErrorSolicitud("formato", "Formato no permitido. Usa JPG, PNG o WebP.", 415)
    return datos


def _crear_registro(fuente, resultado):
    """Guarda el resultado anónimo del rostro principal (sin imagen)."""
    principal = resultado.get("principal") or {}
    return Analisis.objects.create(
        fuente=fuente,
        cantidad_rostros=resultado.get("cantidad_rostros", 0),
        emocion_principal=principal.get("emocion", ""),
        puntuacion=principal.get("puntuacion"),
        puntuaciones=principal.get("puntuaciones", []),
        tiempo_ms=resultado.get("tiempo_ms", 0),
    )


def registrar_foto(resultado):
    """Registra siempre el resultado de una foto."""
    return _crear_registro(Analisis.Fuente.FOTO, resultado)


def registrar_camara(request, resultado, ahora=None):
    """Registra el resultado de la cámara como máximo una vez cada 5 s por sesión.

    Solo se registran fotogramas con al menos un rostro, para no llenar la
    base de datos con fotogramas vacíos.

    Returns:
        El ``Analisis`` creado, o None si no correspondía registrar.
    """
    if not resultado.get("cantidad_rostros"):
        return None
    ahora = time.time() if ahora is None else ahora
    ultimo = request.session.get(CLAVE_SESION_CAMARA, 0)
    if ahora - ultimo < INTERVALO_REGISTRO_CAMARA:
        return None
    request.session[CLAVE_SESION_CAMARA] = ahora
    return _crear_registro(Analisis.Fuente.CAMARA, resultado)
