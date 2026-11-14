"""
Descarga los modelos de visión artificial que usa EmoSense.

Modelos:
    - deploy.prototxt y res10_300x300_ssd_iter_140000.caffemodel:
      detector de rostros Res10 SSD (cv2.dnn.readNetFromCaffe).
    - emotion-ferplus-8.onnx: clasificador de expresiones FER+
      (cv2.dnn.readNetFromONNX).

Los archivos se guardan en la carpeta ``modelos_ia/``. Si un archivo ya existe
(y no está vacío) se omite.

Uso:
    python descargar_modelos.py
"""

import sys
import urllib.request
from pathlib import Path

CARPETA_MODELOS = Path(__file__).resolve().parent / "modelos_ia"

MODELOS = {
    "deploy.prototxt": (
        "https://raw.githubusercontent.com/opencv/opencv/master/"
        "samples/dnn/face_detector/deploy.prototxt"
    ),
    "res10_300x300_ssd_iter_140000.caffemodel": (
        "https://raw.githubusercontent.com/opencv/opencv_3rdparty/"
        "dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
    ),
    "emotion-ferplus-8.onnx": (
        "https://media.githubusercontent.com/media/onnx/models/main/validated/"
        "vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
    ),
}


def _formatear_mb(num_bytes):
    """Devuelve un tamaño en bytes como texto en megabytes (p. ej. '10.4 MB')."""
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def _mostrar_progreso(bloques, tamano_bloque, tamano_total):
    """Imprime el progreso de la descarga en la misma línea de la consola.

    Se usa como ``reporthook`` de ``urllib.request.urlretrieve``.
    """
    descargado = bloques * tamano_bloque
    if tamano_total > 0:
        descargado = min(descargado, tamano_total)
        porcentaje = descargado * 100 / tamano_total
        ancho = 30
        lleno = int(ancho * descargado / tamano_total)
        barra = "#" * lleno + "-" * (ancho - lleno)
        sys.stdout.write(
            f"\r   [{barra}] {porcentaje:5.1f}% "
            f"({_formatear_mb(descargado)} de {_formatear_mb(tamano_total)})"
        )
    else:
        sys.stdout.write(f"\r   {_formatear_mb(descargado)} descargados")
    sys.stdout.flush()


def descargar_modelo(nombre, url, carpeta=None):
    """Descarga un modelo si aún no existe en ``carpeta``.

    La descarga se escribe primero en un archivo ``.part`` y solo se renombra
    al terminar, para no dejar archivos incompletos si se interrumpe.

    Args:
        nombre: nombre del archivo de destino.
        url: dirección desde la que se descarga.
        carpeta: carpeta donde se guardará el archivo (por defecto, CARPETA_MODELOS).

    Returns:
        True si se descargó, False si se omitió porque ya existía.
    """
    carpeta = CARPETA_MODELOS if carpeta is None else carpeta
    destino = carpeta / nombre
    if destino.exists() and destino.stat().st_size > 0:
        print(f"[omitido]  {nombre} ya existe ({_formatear_mb(destino.stat().st_size)}).")
        return False

    temporal = destino.with_name(destino.name + ".part")
    print(f"[descarga] {nombre}")
    try:
        urllib.request.urlretrieve(url, temporal, reporthook=_mostrar_progreso)
    except BaseException:
        temporal.unlink(missing_ok=True)
        print()
        raise
    temporal.replace(destino)
    print(f"\n   Guardado en {destino}")
    return True


def main():
    """Descarga todos los modelos y devuelve el código de salida del script."""
    CARPETA_MODELOS.mkdir(parents=True, exist_ok=True)
    errores = []
    for nombre, url in MODELOS.items():
        try:
            descargar_modelo(nombre, url)
        except KeyboardInterrupt:
            print("\nDescarga cancelada por el usuario.")
            return 1
        except Exception as error:  # noqa: BLE001 - se informa y se continúa
            print(f"[error]    No se pudo descargar {nombre}: {error}")
            errores.append(nombre)

    if errores:
        print(f"\nFallaron {len(errores)} descarga(s): {', '.join(errores)}")
        return 1
    print("\nTodos los modelos están listos en", CARPETA_MODELOS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
