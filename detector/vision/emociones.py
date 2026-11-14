"""Clasificación de expresiones faciales con FER+ (OpenCV DNN)."""

import cv2
import numpy as np

from . import config

# Claves en español en el mismo orden que las 7 primeras salidas de FER+.
CLAVES_ES = tuple(config.MAPA_ES[c] for c in config.ORDEN_FERPLUS[: config.CLASES_USADAS])


def softmax(valores):
    """Aplica softmax numéricamente estable a un vector de puntuaciones."""
    valores = np.asarray(valores, dtype=np.float64)
    exp = np.exp(valores - valores.max())
    return exp / exp.sum()


def ampliar_recuadro(rostro, ancho, alto, margen=config.MARGEN_ROSTRO):
    """Amplía el recuadro del rostro un porcentaje por lado sin salir de la imagen.

    Returns:
        Tupla ``(x1, y1, x2, y2)`` en píxeles.
    """
    dx = int(round(rostro["w"] * margen))
    dy = int(round(rostro["h"] * margen))
    x1 = max(0, rostro["x"] - dx)
    y1 = max(0, rostro["y"] - dy)
    x2 = min(ancho, rostro["x"] + rostro["w"] + dx)
    y2 = min(alto, rostro["y"] + rostro["h"] + dy)
    return x1, y1, x2, y2


def preparar_rostro(imagen, rostro):
    """Recorta el rostro (con margen), lo pasa a gris 64x64 y crea el blob 1x1x64x64."""
    alto, ancho = imagen.shape[:2]
    x1, y1, x2, y2 = ampliar_recuadro(rostro, ancho, alto)
    recorte = imagen[y1:y2, x1:x2]
    if recorte.ndim == 3:
        recorte = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    gris = cv2.resize(recorte, config.TAM_ENTRADA_FERPLUS, interpolation=cv2.INTER_AREA)
    # FER+ espera los valores de píxel sin normalizar (0-255).
    return cv2.dnn.blobFromImage(gris, scalefactor=1.0, size=config.TAM_ENTRADA_FERPLUS)


def clasificar_emocion(imagen, rostro, red):
    """Estima la expresión facial visible de un rostro.

    Args:
        imagen: arreglo NumPy BGR (o gris) que contiene el rostro.
        rostro: diccionario ``{x, y, w, h}`` devuelto por ``detectar_rostros``.
        red: red FER+ cargada con ``cv2.dnn.readNetFromONNX``.

    Returns:
        Diccionario ``{emocion, puntuacion, puntuaciones}`` donde
        ``puntuaciones`` es una lista ``[{emocion, puntuacion}]`` ordenada de
        mayor a menor. Se descarta *contempt* y las 7 probabilidades suman 1.
    """
    red.setInput(preparar_rostro(imagen, rostro))
    salida = np.asarray(red.forward()).reshape(-1)[: config.CLASES_USADAS]
    probabilidades = softmax(salida)

    puntuaciones = sorted(
        (
            {"emocion": clave, "puntuacion": round(float(p), 4)}
            for clave, p in zip(CLAVES_ES, probabilidades)
        ),
        key=lambda item: item["puntuacion"],
        reverse=True,
    )
    mejor = puntuaciones[0]
    return {
        "emocion": mejor["emocion"],
        "puntuacion": mejor["puntuacion"],
        "puntuaciones": puntuaciones,
    }
