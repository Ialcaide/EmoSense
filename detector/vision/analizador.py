"""
Punto de entrada del módulo de visión: analiza un fotograma completo.

Flujo: bytes JPEG -> cv2.imdecode (en memoria) -> reducción a 640 px ->
detección de rostros -> clasificación de cada rostro -> evaluación de calidad.
Ninguna imagen se escribe en disco.
"""

import threading
import time

import cv2
import numpy as np

from . import config
from .calidad import evaluar_calidad
from .cargador import obtener_modelos
from .emociones import clasificar_emocion
from .errores import ImagenInvalidaError
from .rostros import detectar_rostros

# Las redes de OpenCV DNN no son seguras para usarse desde varios hilos a la
# vez (runserver atiende peticiones en hilos), así que se serializa su uso.
_CANDADO_REDES = threading.Lock()


def decodificar_imagen(datos):
    """Convierte bytes (JPEG/PNG) en una imagen BGR de NumPy, solo en memoria.

    Raises:
        ImagenInvalidaError: si los datos están vacíos o no son una imagen.
    """
    if not isinstance(datos, (bytes, bytearray, memoryview)):
        raise ImagenInvalidaError("Se esperaban los bytes de una imagen.")
    if len(datos) == 0:
        raise ImagenInvalidaError("La imagen está vacía.")
    arreglo = np.frombuffer(datos, dtype=np.uint8)
    imagen = cv2.imdecode(arreglo, cv2.IMREAD_COLOR)
    if imagen is None or imagen.size == 0:
        raise ImagenInvalidaError("No se pudo decodificar la imagen.")
    return imagen


def reducir_imagen(imagen, lado_max=config.ANCHO_MAX_PROCESO):
    """Reduce la imagen si su lado mayor supera ``lado_max``.

    Returns:
        Tupla ``(imagen_reducida, escala)`` donde ``escala <= 1``.
    """
    alto, ancho = imagen.shape[:2]
    lado_mayor = max(alto, ancho)
    if lado_mayor <= lado_max:
        return imagen, 1.0
    escala = lado_max / lado_mayor
    nuevo = (max(1, int(round(ancho * escala))), max(1, int(round(alto * escala))))
    return cv2.resize(imagen, nuevo, interpolation=cv2.INTER_AREA), escala


def _a_escala_original(rostro, escala, ancho, alto):
    """Convierte las coordenadas de un rostro a la escala de la imagen original."""
    if escala == 1.0:
        return {k: rostro[k] for k in ("x", "y", "w", "h")}
    x = min(ancho, int(round(rostro["x"] / escala)))
    y = min(alto, int(round(rostro["y"] / escala)))
    w = min(ancho - x, int(round(rostro["w"] / escala)))
    h = min(alto - y, int(round(rostro["h"] / escala)))
    return {"x": x, "y": y, "w": w, "h": h}


def analizar_imagen(datos, modelos=None):
    """Analiza un fotograma y estima la expresión de cada rostro visible.

    Args:
        datos: bytes de la imagen (JPEG o PNG).
        modelos: ``Modelos`` a usar; por defecto los de ``obtener_modelos()``.
            Permite inyectar redes falsas en las pruebas.

    Returns:
        Diccionario::

            {
                "ok": True,
                "ancho": int, "alto": int,           # tamaño original
                "cantidad_rostros": int,
                "rostros": [{x, y, w, h, confianza, emocion,
                             puntuacion, puntuaciones}, ...],
                "principal": dict | None,            # el rostro más grande
                "calidad": dict,
                "tiempo_ms": float,
            }

    Raises:
        ImagenInvalidaError: si los bytes no son una imagen válida.
        ModelosNoDisponiblesError: si faltan los archivos de los modelos.
    """
    inicio = time.perf_counter()
    imagen = decodificar_imagen(datos)
    if modelos is None:
        modelos = obtener_modelos()

    alto, ancho = imagen.shape[:2]
    reducida, escala = reducir_imagen(imagen)

    rostros = []
    with _CANDADO_REDES:
        detectados = detectar_rostros(reducida, modelos.red_rostros)
        for rostro in detectados:
            emocion = clasificar_emocion(reducida, rostro, modelos.red_emociones)
            rostros.append(
                {
                    **_a_escala_original(rostro, escala, ancho, alto),
                    "confianza": rostro["confianza"],
                    **emocion,
                }
            )

    # detectar_rostros ya ordena por área: el primero es el principal.
    calidad = evaluar_calidad(reducida, detectados[0] if detectados else None)

    return {
        "ok": True,
        "ancho": ancho,
        "alto": alto,
        "cantidad_rostros": len(rostros),
        "rostros": rostros,
        "principal": rostros[0] if rostros else None,
        "calidad": calidad,
        "tiempo_ms": round((time.perf_counter() - inicio) * 1000, 1),
    }
