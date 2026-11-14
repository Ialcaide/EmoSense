"""Evaluación de las condiciones de captura: brillo, nitidez y distancia."""

import cv2

from . import config

RECOMENDACIONES = {
    ("brillo", "bajo"): "Busca más luz frente a tu rostro 💡",
    ("brillo", "alto"): "Hay demasiada luz; evita la luz directa 😎",
    ("nitidez", "bajo"): "La imagen está borrosa; mantén la cámara estable 📷",
    ("distancia", "bajo"): "Acércate un poco a la cámara 🔍",
    ("distancia", "alto"): "Aléjate un poco de la cámara ↔️",
    ("distancia", "sin_rostro"): "No vemos tu rostro; colócate frente a la cámara 🙂",
}
MENSAJE_OK = "¡Buenas condiciones! ✅"


def _clasificar(valor, minimo, maximo=None):
    """Devuelve 'bajo', 'alto' u 'ok' según el rango permitido."""
    if valor < minimo:
        return "bajo"
    if maximo is not None and valor > maximo:
        return "alto"
    return "ok"


def evaluar_calidad(imagen, rostro=None):
    """Evalúa si la imagen es adecuada para estimar la expresión.

    El brillo y la nitidez se miden sobre el rostro si existe; si no, sobre
    toda la imagen.

    Args:
        imagen: arreglo NumPy BGR o en gris.
        rostro: diccionario ``{x, y, w, h}`` o ``None`` si no hay rostro.

    Returns:
        Diccionario con ``brillo``, ``nitidez`` y ``distancia`` (cada uno con
        ``valor`` y ``estado``), ``apta`` (bool) y ``recomendaciones`` (lista).
        Estados posibles: ``ok``, ``bajo``, ``alto`` o ``sin_rostro``.
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY) if imagen.ndim == 3 else imagen
    ancho_imagen = gris.shape[1]

    region = gris
    if rostro is not None:
        recorte = gris[rostro["y"]: rostro["y"] + rostro["h"], rostro["x"]: rostro["x"] + rostro["w"]]
        if recorte.size:
            region = recorte

    brillo = float(region.mean())
    nitidez = float(cv2.Laplacian(region, cv2.CV_64F).var())

    resultado = {
        "brillo": {
            "valor": round(brillo, 1),
            "estado": _clasificar(brillo, config.BRILLO_MIN, config.BRILLO_MAX),
        },
        "nitidez": {
            "valor": round(nitidez, 1),
            "estado": _clasificar(nitidez, config.NITIDEZ_MIN),
        },
    }

    if rostro is None:
        resultado["distancia"] = {"valor": None, "estado": "sin_rostro"}
    else:
        distancia = rostro["w"] / ancho_imagen
        resultado["distancia"] = {
            "valor": round(distancia, 3),
            "estado": _clasificar(distancia, config.DISTANCIA_MIN, config.DISTANCIA_MAX),
        }

    recomendaciones = [
        RECOMENDACIONES[(medida, resultado[medida]["estado"])]
        for medida in ("distancia", "brillo", "nitidez")
        if resultado[medida]["estado"] != "ok"
    ]
    resultado["apta"] = not recomendaciones
    resultado["recomendaciones"] = recomendaciones or [MENSAJE_OK]
    return resultado
