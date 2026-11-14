"""Vistas de la app 'detector': entrenador, API de análisis y API de práctica."""

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from . import amabilidad, servicios
from .emociones_info import BUENAS_PRACTICAS, CONSEJOS_CAMARA, emociones_para_frontend, guia_expresiones
from .models import SesionPractica
from .vision import ImagenInvalidaError, ModelosNoDisponiblesError, analizar_imagen


def configuracion_practica():
    """Datos del medidor de amabilidad que necesita el navegador (json_script)."""
    return {
        "url": reverse("api:practica"),
        "duracion": amabilidad.DURACION_PRACTICA,
        "emociones_amables": list(amabilidad.EMOCIONES_AMABLES),
        "umbral_excelente": amabilidad.UMBRAL_EXCELENTE,
        "umbral_bueno": amabilidad.UMBRAL_BUENO,
        "niveles": amabilidad.NIVELES,
        "consejo_por_expresion": amabilidad.CONSEJO_POR_EXPRESION,
        "consejo_sin_predominante": amabilidad.CONSEJO_SIN_PREDOMINANTE,
    }


@ensure_csrf_cookie
def index(request):
    """Muestra el entrenador: cámara, foto, medidor de amabilidad y guía.

    Garantiza la cookie CSRF para que el JavaScript pueda enviarla en el
    header X-CSRFToken.
    """
    contexto = {
        "emociones": emociones_para_frontend(),
        "guia": guia_expresiones(),
        "buenas_practicas": BUENAS_PRACTICAS,
        "consejos": CONSEJOS_CAMARA,
        "practica": configuracion_practica(),
    }
    return render(request, "detector/index.html", contexto)


def respuesta_error(codigo, mensaje, estado):
    """Devuelve un error JSON con el formato {ok: false, codigo, mensaje}."""
    return JsonResponse({"ok": False, "codigo": codigo, "mensaje": mensaje}, status=estado)


def _procesar(request, fuente):
    """Valida la imagen, la analiza en memoria y registra el resultado anónimo."""
    es_foto = fuente == "foto"
    try:
        datos = servicios.leer_imagen(request, validar_formato=es_foto)
        resultado = analizar_imagen(datos)
    except servicios.ErrorSolicitud as error:
        return respuesta_error(error.codigo, error.mensaje, error.estado)
    except ImagenInvalidaError:
        return respuesta_error("imagen_invalida", "No se pudo leer la imagen. Intenta con otra.", 400)
    except ModelosNoDisponiblesError:
        return respuesta_error(
            "sin_modelos",
            "Los modelos de visión no están disponibles. Ejecute python descargar_modelos.py",
            503,
        )

    # Los bytes de la imagen se descartan al terminar la petición: solo se
    # registra el resultado anónimo.
    if es_foto:
        servicios.registrar_foto(resultado)
    else:
        servicios.registrar_camara(request, resultado)
    return JsonResponse(resultado)


@require_POST
def api_analizar(request):
    """POST /api/analizar/: analiza un fotograma de la cámara (campo 'imagen')."""
    return _procesar(request, "camara")


@require_POST
def api_foto(request):
    """POST /api/foto/: analiza una foto JPG, PNG o WebP (campo 'imagen')."""
    return _procesar(request, "foto")


@require_POST
def api_practica(request):
    """POST /api/practica/: guarda una sesión del medidor de amabilidad.

    Cuerpo JSON: ``{duracion, cantidad_analisis, amables, predominante}``.
    El servidor calcula el porcentaje y responde 201 con
    ``{ok, id, porcentaje, nivel, mensaje, consejos}``.
    """
    try:
        cuerpo = json.loads(request.body or b"")
    except (ValueError, UnicodeDecodeError):
        return respuesta_error("json_invalido", "El cuerpo debe ser JSON válido.", 400)

    try:
        datos = amabilidad.validar_sesion(cuerpo)
    except ValueError as error:
        return respuesta_error("datos_invalidos", str(error), 400)

    porcentaje = amabilidad.calcular_porcentaje(datos["amables"], datos["cantidad_analisis"])
    sesion = SesionPractica.objects.create(
        duracion=datos["duracion"],
        porcentaje_amable=porcentaje,
        cantidad_analisis=datos["cantidad_analisis"],
    )
    resultado = amabilidad.evaluar_sesion(porcentaje, datos["predominante"])
    return JsonResponse({"ok": True, "id": sesion.id, "porcentaje": porcentaje, **resultado}, status=201)
