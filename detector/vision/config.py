"""
Parámetros del módulo de visión.

Reúne en un solo lugar las rutas de los modelos, los umbrales de detección
y de calidad, y el orden de las clases de FER+.
"""

from pathlib import Path


def _carpeta_modelos():
    """Devuelve la carpeta de modelos definida en settings.CARPETA_MODELOS.

    Si Django no está configurado (por ejemplo, al usar el módulo desde un
    script), usa ``<raíz del proyecto>/modelos_ia``.
    """
    try:
        from django.conf import settings

        return Path(settings.CARPETA_MODELOS)
    except Exception:  # noqa: BLE001 - Django sin configurar o sin el ajuste
        return Path(__file__).resolve().parents[2] / "modelos_ia"


# --- Rutas de los modelos ---------------------------------------------------

CARPETA_MODELOS = _carpeta_modelos()
RUTA_PROTOTXT = CARPETA_MODELOS / "deploy.prototxt"
RUTA_CAFFEMODEL = CARPETA_MODELOS / "res10_300x300_ssd_iter_140000.caffemodel"
RUTA_FERPLUS = CARPETA_MODELOS / "emotion-ferplus-8.onnx"


# --- Detección de rostros (Res10 SSD) ---------------------------------------

UMBRAL_ROSTRO = 0.6          # Confianza mínima para aceptar un rostro.
TAM_MIN_ROSTRO = 30          # Ancho/alto mínimo del rostro en píxeles.
ANCHO_MAX_PROCESO = 640      # Lado mayor máximo con el que se procesa la imagen.
MARGEN_ROSTRO = 0.12         # Ampliación del recuadro antes de clasificar (12 %).

TAM_ENTRADA_RES10 = (300, 300)
MEDIA_RES10 = (104.0, 177.0, 123.0)


# --- Clasificación de expresiones (FER+) ------------------------------------

TAM_ENTRADA_FERPLUS = (64, 64)

# Orden de las 8 salidas del modelo emotion-ferplus-8.onnx.
ORDEN_FERPLUS = (
    "neutral",
    "happiness",
    "surprise",
    "sadness",
    "anger",
    "disgust",
    "fear",
    "contempt",  # Se descarta: EmoSense trabaja con 7 expresiones.
)

# Cantidad de salidas que se usan (las 7 primeras, sin contempt).
CLASES_USADAS = 7

# Traducción de las clases de FER+ a las claves en español (sin tilde).
MAPA_ES = {
    "neutral": "neutral",
    "happiness": "alegria",
    "surprise": "sorpresa",
    "sadness": "tristeza",
    "anger": "enojo",
    "disgust": "disgusto",
    "fear": "miedo",
}


# --- Calidad de la imagen ---------------------------------------------------

BRILLO_MIN = 70              # Media en escala de grises (0-255).
BRILLO_MAX = 200
NITIDEZ_MIN = 60             # Varianza del Laplaciano.
DISTANCIA_MIN = 0.15         # Ancho del rostro / ancho de la imagen.
DISTANCIA_MAX = 0.60
