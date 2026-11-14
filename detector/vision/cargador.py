"""
Carga de los modelos de OpenCV DNN.

Los modelos se cargan una sola vez por proceso gracias a ``lru_cache`` y se
ejecutan en CPU.
"""

from functools import lru_cache
from typing import NamedTuple

import cv2

from . import config
from .errores import ModelosNoDisponiblesError


class Modelos(NamedTuple):
    """Par de redes que usa el analizador."""

    red_rostros: cv2.dnn.Net
    red_emociones: cv2.dnn.Net


def _usar_cpu(red):
    """Configura una red para ejecutarse con el backend de OpenCV en CPU."""
    red.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    red.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return red


def verificar_archivos():
    """Comprueba que existan los tres archivos de modelos.

    Raises:
        ModelosNoDisponiblesError: si falta alguno, indicando cuáles.
    """
    rutas = (config.RUTA_PROTOTXT, config.RUTA_CAFFEMODEL, config.RUTA_FERPLUS)
    faltantes = [r.name for r in rutas if not r.is_file() or r.stat().st_size == 0]
    if faltantes:
        raise ModelosNoDisponiblesError(
            f"Faltan modelos en {config.CARPETA_MODELOS}: {', '.join(faltantes)}. "
            "Ejecute python descargar_modelos.py"
        )


@lru_cache(maxsize=1)
def obtener_modelos():
    """Carga Res10 SSD (Caffe) y FER+ (ONNX) una sola vez y los devuelve.

    Returns:
        Modelos: tupla con ``red_rostros`` y ``red_emociones``.

    Raises:
        ModelosNoDisponiblesError: si falta un archivo o OpenCV no puede leerlo.
    """
    verificar_archivos()
    try:
        red_rostros = cv2.dnn.readNetFromCaffe(
            str(config.RUTA_PROTOTXT), str(config.RUTA_CAFFEMODEL)
        )
        red_emociones = cv2.dnn.readNetFromONNX(str(config.RUTA_FERPLUS))
    except cv2.error as error:
        raise ModelosNoDisponiblesError(
            f"No se pudieron cargar los modelos ({error}). "
            "Ejecute python descargar_modelos.py"
        ) from error
    return Modelos(_usar_cpu(red_rostros), _usar_cpu(red_emociones))
