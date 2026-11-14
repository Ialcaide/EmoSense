"""Detección de rostros con Res10 SSD (OpenCV DNN)."""

import cv2

from . import config


def detectar_rostros(imagen, red, umbral=config.UMBRAL_ROSTRO, tam_min=config.TAM_MIN_ROSTRO):
    """Detecta rostros en una imagen BGR.

    Args:
        imagen: arreglo NumPy BGR (alto x ancho x 3).
        red: red Res10 SSD cargada con ``cv2.dnn.readNetFromCaffe``.
        umbral: confianza mínima para aceptar una detección.
        tam_min: ancho y alto mínimos (en píxeles) de un rostro válido.

    Returns:
        Lista de diccionarios ``{x, y, w, h, confianza}`` ordenada de mayor a
        menor área. Las coordenadas están recortadas a los límites de la imagen.
    """
    alto, ancho = imagen.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(imagen, config.TAM_ENTRADA_RES10),
        scalefactor=1.0,
        size=config.TAM_ENTRADA_RES10,
        mean=config.MEDIA_RES10,
    )
    red.setInput(blob)
    detecciones = red.forward()  # Forma (1, 1, N, 7)

    rostros = []
    for deteccion in detecciones.reshape(-1, 7):
        confianza = float(deteccion[2])
        if confianza < umbral:
            continue
        # Coordenadas normalizadas (0-1) -> píxeles, recortadas a la imagen.
        x1 = max(0, min(ancho, int(round(deteccion[3] * ancho))))
        y1 = max(0, min(alto, int(round(deteccion[4] * alto))))
        x2 = max(0, min(ancho, int(round(deteccion[5] * ancho))))
        y2 = max(0, min(alto, int(round(deteccion[6] * alto))))
        w, h = x2 - x1, y2 - y1
        if w < tam_min or h < tam_min:
            continue
        rostros.append({"x": x1, "y": y1, "w": w, "h": h, "confianza": round(confianza, 4)})

    rostros.sort(key=lambda r: r["w"] * r["h"], reverse=True)
    return rostros
