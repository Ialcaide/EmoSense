"""Pruebas de la app 'detector': entrenador, módulo de visión, APIs y medidor de amabilidad."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.html import escape

from detector import amabilidad, servicios
from detector.emociones_info import (
    BUENAS_PRACTICAS,
    CONSEJOS_CAMARA,
    EMOCIONES,
    emociones_para_frontend,
    emociones_por_rol,
    guia_expresiones,
)
from detector.models import Analisis, SesionPractica
from detector.vision import ImagenInvalidaError, ModelosNoDisponiblesError, analizar_imagen
from detector.vision.calidad import evaluar_calidad
from detector.vision.cargador import Modelos, verificar_archivos
from detector.vision.config import MAPA_ES
from detector.vision.emociones import clasificar_emocion
from detector.vision.rostros import detectar_rostros


class DetectorIndexTests(TestCase):
    """Verifica la página del detector en vivo."""

    def test_index_responde_200(self):
        """La página principal debe responder con código 200."""
        respuesta = self.client.get(reverse("detector:index"))
        self.assertEqual(respuesta.status_code, 200)

    def test_index_hereda_de_base(self):
        """La página debe usar su plantilla y heredar de base.html."""
        respuesta = self.client.get(reverse("detector:index"))
        self.assertTemplateUsed(respuesta, "detector/index.html")
        self.assertTemplateUsed(respuesta, "base.html")

    def test_enlace_activo(self):
        """El enlace de navegación de esta sección debe marcarse como actual."""
        respuesta = self.client.get(reverse("detector:index"))
        self.assertContains(respuesta, 'aria-current="page"', count=1)

    def test_emociones_en_json_script(self):
        """Las 7 emociones llegan al navegador con json_script y como barras."""
        respuesta = self.client.get(reverse("detector:index"))
        self.assertContains(respuesta, '<script id="datos-emociones" type="application/json">')
        self.assertContains(respuesta, 'data-puntaje="', count=7)
        self.assertEqual(set(respuesta.context["emociones"]), set(EMOCIONES))

    def test_cookie_csrf(self):
        """La página debe entregar la cookie CSRF que usa detector.js."""
        respuesta = self.client.get(reverse("detector:index"))
        self.assertIn("csrftoken", respuesta.cookies)

    def test_urls_api_y_pantalla_carga(self):
        """La página expone las URLs de la API y muestra la pantalla de carga inicial."""
        respuesta = self.client.get(reverse("detector:index"))
        self.assertContains(respuesta, f'data-url-analizar="{reverse("api:analizar")}"')
        self.assertContains(respuesta, f'data-url-foto="{reverse("api:foto")}"')
        self.assertContains(respuesta, 'id="pantalla-carga" role="status" aria-live="polite" data-inicial')


class GuiaExpresionesTests(TestCase):
    """Sección desplegable 'Guía de atención' del entrenador."""

    def setUp(self):
        self.respuesta = self.client.get(reverse("detector:index"))
        self.html = self.respuesta.content.decode()

    def test_details_cerrado_por_defecto(self):
        """La guía usa <details id="guia"> sin el atributo open (ancla de la navegación)."""
        self.assertIn('<details class="guia" id="guia">', self.html)
        self.assertContains(self.respuesta, "Guía de atención")

    def test_dos_grupos_por_rol(self):
        """La guía se divide en expresiones propias (2) y del cliente (5)."""
        self.assertContains(self.respuesta, "Expresiones que debes mostrar")
        self.assertContains(self.respuesta, "Expresiones del cliente que debes reconocer")
        self.assertEqual(self.html.count('data-rol="propia"'), 2)
        self.assertEqual(self.html.count('data-rol="cliente"'), 5)
        # El grupo propio aparece antes que el del cliente.
        self.assertLess(self.html.index('data-rol="propia"'), self.html.index('data-rol="cliente"'))

    def test_siete_tarjetas_con_guia_y_consejo(self):
        """Cada tarjeta tiene las 4 partes, su consejo de atención y su situación."""
        self.assertEqual(self.html.count('class="tarjeta guia__tarjeta" data-emocion='), 7)
        for clave, info in EMOCIONES.items():
            with self.subTest(emocion=clave):
                self.assertIn(f'data-emocion="{clave}" data-rol="{info["rol"]}" style="--emo: {info["color"]}"', self.html)
                for texto in info["guia"].values():
                    self.assertContains(self.respuesta, escape(texto))
                self.assertContains(self.respuesta, escape(info["consejo_atencion"]))
                self.assertContains(self.respuesta, escape(info["situacion"]))
        for etiqueta in ("Cejas", "Ojos", "Nariz", "Boca"):
            self.assertEqual(self.html.count(f"</span> {etiqueta}</dt>"), 7)

    def test_buenas_practicas_y_consejos_camara(self):
        """Incluye las tarjetas 'Buenas prácticas' y 'Consejos para la cámara'."""
        self.assertContains(self.respuesta, "Buenas prácticas")
        for practica in BUENAS_PRACTICAS:
            self.assertContains(self.respuesta, escape(practica["texto"]))
        self.assertContains(self.respuesta, "Consejos para la cámara")
        for consejo in CONSEJOS_CAMARA:
            self.assertContains(self.respuesta, escape(consejo["texto"]))


class GuiaDatosTests(SimpleTestCase):
    """Datos de la guía generados desde emociones_info.py."""

    def test_estructura(self):
        """Dos grupos (propia, cliente); cada emoción con 4 filas y su consejo."""
        guia = guia_expresiones()
        self.assertEqual([g["rol"] for g in guia], ["propia", "cliente"])
        self.assertEqual([e["clave"] for e in guia[0]["emociones"]], ["alegria", "neutral"])
        self.assertEqual(
            [e["clave"] for e in guia[1]["emociones"]], ["tristeza", "enojo", "sorpresa", "miedo", "disgusto"]
        )
        for grupo in guia:
            for emo in grupo["emociones"]:
                self.assertEqual([f["parte"] for f in emo["filas"]], ["Cejas", "Ojos", "Nariz", "Boca"])
                self.assertEqual(emo["filas"][0]["texto"], EMOCIONES[emo["clave"]]["guia"]["cejas"])
                self.assertEqual(emo["consejo_atencion"], EMOCIONES[emo["clave"]]["consejo_atencion"])

    def test_buenas_practicas(self):
        """Hay 4 buenas prácticas: contacto visual, sonrisa, postura y tono de voz."""
        titulos = [p["titulo"] for p in BUENAS_PRACTICAS]
        self.assertEqual(titulos, ["Contacto visual", "Sonrisa natural", "Postura", "Tono de voz"])

    def test_cuatro_consejos(self):
        """Hay 4 consejos, cada uno con emoji, título y texto."""
        self.assertEqual(len(CONSEJOS_CAMARA), 4)
        for consejo in CONSEJOS_CAMARA:
            self.assertEqual(set(consejo), {"emoji", "titulo", "texto"})


class EmocionesFrontendTests(SimpleTestCase):
    """GIF opcional por emoción en los datos del frontend."""

    def test_sin_gif_no_agrega_clave(self):
        """Si no existe el GIF, la emoción no lleva la clave 'gif'."""
        with tempfile.TemporaryDirectory() as carpeta, self.settings(STATICFILES_DIRS=[carpeta]):
            datos = emociones_para_frontend()
        self.assertTrue(all("gif" not in info for info in datos.values()))

    def test_con_gif_agrega_url(self):
        """Si existe static/gifs/<clave>.gif, se agrega su URL."""
        with tempfile.TemporaryDirectory() as carpeta:
            Path(carpeta, "gifs").mkdir()
            Path(carpeta, "gifs", "alegria.gif").write_bytes(b"GIF89a")
            with self.settings(STATICFILES_DIRS=[carpeta]):
                datos = emociones_para_frontend()
        self.assertEqual(datos["alegria"]["gif"], "/static/gifs/alegria.gif")
        self.assertNotIn("gif", datos["tristeza"])
        self.assertNotIn("gif", EMOCIONES["alegria"])  # no modifica el original


# --- Redes falsas para probar sin descargar los modelos ---------------------


class RedFalsa:
    """Imita una cv2.dnn.Net: guarda la entrada y devuelve una salida fija."""

    def __init__(self, salida):
        self.salida = np.asarray(salida, dtype=np.float32)
        self.entrada = None

    def setInput(self, blob):  # noqa: N802 - mismo nombre que en OpenCV
        """Guarda el blob recibido."""
        self.entrada = blob

    def forward(self):
        """Devuelve la salida configurada."""
        return self.salida


def _deteccion(confianza, x1, y1, x2, y2):
    """Crea una fila de detección Res10 con coordenadas normalizadas (0-1)."""
    return [0, 1, confianza, x1, y1, x2, y2]


def _jpeg(imagen):
    """Codifica una imagen como JPEG en memoria y devuelve sus bytes."""
    ok, buffer = cv2.imencode(".jpg", imagen)
    assert ok
    return buffer.tobytes()


# Salida FER+ falsa: contempt (última) es enorme, pero debe descartarse.
SALIDA_FERPLUS = [[1.0, 5.0, 0.5, 0.2, 0.1, 0.0, 0.3, 50.0]]


class AnalizadorEntradaTests(SimpleTestCase):
    """Validación de los bytes de entrada (no requiere modelos)."""

    def test_bytes_invalidos(self):
        """Bytes que no son una imagen deben lanzar ImagenInvalidaError."""
        with self.assertRaises(ImagenInvalidaError):
            analizar_imagen(b"esto no es un jpeg")

    def test_imagen_vacia(self):
        """Bytes vacíos deben lanzar ImagenInvalidaError."""
        with self.assertRaises(ImagenInvalidaError):
            analizar_imagen(b"")

    def test_tipo_incorrecto(self):
        """Un valor que no son bytes debe lanzar ImagenInvalidaError."""
        with self.assertRaises(ImagenInvalidaError):
            analizar_imagen("texto")


class ClasificacionTests(SimpleTestCase):
    """Clasificación de expresiones con una red FER+ falsa."""

    def setUp(self):
        self.imagen = np.full((200, 200, 3), 128, dtype=np.uint8)
        self.rostro = {"x": 50, "y": 50, "w": 100, "h": 100}
        self.red = RedFalsa(SALIDA_FERPLUS)

    def test_descarta_contempt_y_suma_uno(self):
        """Debe devolver 7 clases en español, sin contempt, que sumen 1."""
        resultado = clasificar_emocion(self.imagen, self.rostro, self.red)
        claves = [p["emocion"] for p in resultado["puntuaciones"]]
        self.assertEqual(len(claves), 7)
        self.assertNotIn("contempt", claves)
        self.assertEqual(set(claves), set(MAPA_ES.values()))
        total = sum(p["puntuacion"] for p in resultado["puntuaciones"])
        self.assertAlmostEqual(total, 1.0, delta=1e-3)

    def test_emocion_principal_y_orden(self):
        """La mayor salida (happiness) debe traducirse a 'alegria' y ir primero."""
        resultado = clasificar_emocion(self.imagen, self.rostro, self.red)
        self.assertEqual(resultado["emocion"], "alegria")
        valores = [p["puntuacion"] for p in resultado["puntuaciones"]]
        self.assertEqual(valores, sorted(valores, reverse=True))

    def test_blob_gris_64x64(self):
        """La red debe recibir un blob de forma 1x1x64x64."""
        clasificar_emocion(self.imagen, self.rostro, self.red)
        self.assertEqual(self.red.entrada.shape, (1, 1, 64, 64))


class RostrosTests(SimpleTestCase):
    """Detección de rostros con una red Res10 falsa."""

    def test_filtra_recorta_y_ordena(self):
        """Filtra por umbral y tamaño, recorta a la imagen y ordena por área."""
        detecciones = np.array([[[
            _deteccion(0.9, 0.1, 0.1, 0.3, 0.3),      # 40x40 px
            _deteccion(0.95, 0.4, 0.4, 1.2, 1.1),     # sale de la imagen: se recorta
            _deteccion(0.3, 0.0, 0.0, 0.5, 0.5),      # baja confianza: descartado
            _deteccion(0.99, 0.0, 0.0, 0.05, 0.05),   # 10 px: descartado
        ]]], dtype=np.float32)
        imagen = np.zeros((200, 200, 3), dtype=np.uint8)
        rostros = detectar_rostros(imagen, RedFalsa(detecciones))
        self.assertEqual(len(rostros), 2)
        self.assertEqual(rostros[0], {"x": 80, "y": 80, "w": 120, "h": 120, "confianza": 0.95})
        self.assertEqual(rostros[1]["w"], 40)


class CalidadTests(SimpleTestCase):
    """Evaluación de brillo, nitidez y distancia."""

    def test_imagen_oscura(self):
        """Una imagen oscura debe marcar brillo bajo y recomendar más luz."""
        oscura = np.full((240, 320, 3), 20, dtype=np.uint8)
        calidad = evaluar_calidad(oscura, {"x": 100, "y": 60, "w": 100, "h": 100})
        self.assertEqual(calidad["brillo"]["estado"], "bajo")
        self.assertFalse(calidad["apta"])
        self.assertIn("Busca más luz frente a tu rostro 💡", calidad["recomendaciones"])

    def test_sin_rostro(self):
        """Sin rostro, la distancia debe ser 'sin_rostro'."""
        calidad = evaluar_calidad(np.full((100, 100, 3), 128, dtype=np.uint8), None)
        self.assertEqual(calidad["distancia"]["estado"], "sin_rostro")
        self.assertIsNone(calidad["distancia"]["valor"])

    def test_buenas_condiciones(self):
        """Brillo medio, textura nítida y rostro a buena distancia deben ser aptos."""
        rng = np.random.default_rng(0)
        imagen = rng.integers(60, 200, size=(240, 320, 3), dtype=np.uint8)
        calidad = evaluar_calidad(imagen, {"x": 100, "y": 60, "w": 100, "h": 100})
        self.assertTrue(calidad["apta"])
        self.assertEqual(calidad["recomendaciones"], ["¡Buenas condiciones! ✅"])


class AnalizadorTests(SimpleTestCase):
    """Análisis completo con redes falsas inyectadas."""

    def test_reduce_y_devuelve_coordenadas_originales(self):
        """Una imagen de 1280 px se procesa a 640 px y devuelve coordenadas originales."""
        detecciones = np.array([[[_deteccion(0.9, 0.25, 0.25, 0.5, 0.75)]]], dtype=np.float32)
        modelos = Modelos(RedFalsa(detecciones), RedFalsa(SALIDA_FERPLUS))
        imagen = np.full((720, 1280, 3), 128, dtype=np.uint8)

        resultado = analizar_imagen(_jpeg(imagen), modelos=modelos)

        self.assertTrue(resultado["ok"])
        self.assertEqual((resultado["ancho"], resultado["alto"]), (1280, 720))
        self.assertEqual(resultado["cantidad_rostros"], 1)
        principal = resultado["principal"]
        self.assertEqual(principal["emocion"], "alegria")
        self.assertAlmostEqual(principal["x"], 320, delta=2)
        self.assertAlmostEqual(principal["w"], 320, delta=2)
        self.assertAlmostEqual(principal["h"], 360, delta=2)
        self.assertIn("calidad", resultado)
        self.assertGreaterEqual(resultado["tiempo_ms"], 0)

    def test_sin_rostros(self):
        """Sin detecciones, principal es None y la calidad indica 'sin_rostro'."""
        modelos = Modelos(RedFalsa(np.zeros((1, 1, 0, 7))), RedFalsa(SALIDA_FERPLUS))
        imagen = np.full((100, 100, 3), 128, dtype=np.uint8)
        resultado = analizar_imagen(_jpeg(imagen), modelos=modelos)
        self.assertEqual(resultado["cantidad_rostros"], 0)
        self.assertIsNone(resultado["principal"])
        self.assertEqual(resultado["calidad"]["distancia"]["estado"], "sin_rostro")


class EmocionesInfoTests(SimpleTestCase):
    """Coherencia de los datos educativos con el módulo de visión."""

    def test_claves_coinciden_con_vision(self):
        """EMOCIONES debe tener exactamente las 7 claves que devuelve la visión."""
        self.assertEqual(set(EMOCIONES), set(MAPA_ES.values()))

    def test_campos_completos(self):
        """Cada emoción tiene exactamente los campos esperados y la guía completa."""
        campos = {"nombre", "emoji", "color", "rol", "descripcion", "consejo_atencion", "situacion", "guia"}
        for clave, datos in EMOCIONES.items():
            with self.subTest(emocion=clave):
                self.assertEqual(set(datos), campos)
                self.assertEqual(set(datos["guia"]), {"cejas", "ojos", "nariz", "boca"})
                self.assertTrue(datos["consejo_atencion"] and datos["situacion"])

    def test_roles(self):
        """Alegría y neutral son 'propia'; las otras 5 son 'cliente'."""
        self.assertEqual(emociones_por_rol("propia"), ["alegria", "neutral"])
        self.assertEqual(emociones_por_rol("cliente"), ["tristeza", "enojo", "sorpresa", "miedo", "disgusto"])
        self.assertEqual(
            EMOCIONES["enojo"]["consejo_atencion"],
            "Mantén la calma, escucha sin interrumpir y ofrece una solución concreta.",
        )
        self.assertEqual(EMOCIONES["enojo"]["situacion"], "Un cliente reclama porque su pedido llegó tarde.")


# --- Medidor de amabilidad y SesionPractica -----------------------------------


class AmabilidadLogicaTests(SimpleTestCase):
    """Funciones puras del medidor de amabilidad."""

    def test_emociones_amables(self):
        """Solo alegría y neutral cuentan como amables."""
        self.assertEqual(amabilidad.EMOCIONES_AMABLES, ("alegria", "neutral"))
        self.assertTrue(amabilidad.es_amable("alegria"))
        self.assertFalse(amabilidad.es_amable("enojo"))
        self.assertFalse(amabilidad.es_amable(None))

    def test_calcular_porcentaje(self):
        """Porcentaje redondeado a 1 decimal; sin análisis lanza ValueError."""
        self.assertEqual(amabilidad.calcular_porcentaje(8, 10), 80.0)
        self.assertEqual(amabilidad.calcular_porcentaje(2, 3), 66.7)
        self.assertEqual(amabilidad.calcular_porcentaje(0, 5), 0.0)
        with self.assertRaises(ValueError):
            amabilidad.calcular_porcentaje(0, 0)

    def test_umbrales(self):
        """≥80 excelente, 50–79 bueno, <50 mejorar (con sus mensajes)."""
        casos = [
            (100, "excelente", "¡Excelente actitud!"),
            (80, "excelente", "¡Excelente actitud!"),
            (79.9, "bueno", "Buen trabajo, sigue practicando"),
            (50, "bueno", "Buen trabajo, sigue practicando"),
            (49.9, "mejorar", "Intenta mantener una expresión más amable"),
            (0, "mejorar", "Intenta mantener una expresión más amable"),
        ]
        for porcentaje, nivel, mensaje in casos:
            with self.subTest(porcentaje=porcentaje):
                resultado = amabilidad.evaluar_sesion(porcentaje)
                self.assertEqual(resultado["nivel"], nivel)
                self.assertEqual(resultado["mensaje"], mensaje)

    def test_tres_consejos(self):
        """2 consejos fijos del nivel + 1 según la expresión predominante."""
        con_enojo = amabilidad.evaluar_sesion(40, "enojo")
        self.assertEqual(len(con_enojo["consejos"]), 3)
        self.assertEqual(con_enojo["consejos"][:2], amabilidad.NIVELES["mejorar"]["consejos"])
        self.assertEqual(con_enojo["consejos"][2], amabilidad.CONSEJO_POR_EXPRESION["enojo"])
        sin_predominante = amabilidad.evaluar_sesion(95, None)
        self.assertEqual(sin_predominante["consejos"][2], amabilidad.CONSEJO_SIN_PREDOMINANTE)

    def test_consejo_para_cada_expresion_del_cliente(self):
        """Hay un consejo de mejora para cada expresión no amable."""
        self.assertEqual(set(amabilidad.CONSEJO_POR_EXPRESION), set(emociones_por_rol("cliente")))

    def test_validar_sesion(self):
        """Acepta datos correctos y rechaza los incoherentes."""
        valida = {"duracion": 60, "cantidad_analisis": 100, "amables": 85, "predominante": "enojo"}
        self.assertEqual(amabilidad.validar_sesion(valida)["amables"], 85)
        self.assertIsNone(amabilidad.validar_sesion({**valida, "predominante": None})["predominante"])
        invalidas = {
            "no es objeto": [],
            "sin análisis": {**valida, "cantidad_analisis": 0},
            "amables > total": {**valida, "amables": 101},
            "duración > 60": {**valida, "duracion": 61},
            "duración texto": {**valida, "duracion": "60"},
            "booleano": {**valida, "amables": True},
            "predominante amable": {**valida, "predominante": "alegria"},
            "predominante desconocida": {**valida, "predominante": "contempt"},
            "demasiados análisis": {**valida, "cantidad_analisis": 10_000},
        }
        for nombre, datos in invalidas.items():
            with self.subTest(caso=nombre), self.assertRaises(ValueError):
                amabilidad.validar_sesion(datos)


class ApiPracticaTests(TestCase):
    """POST /api/practica/ y modelo SesionPractica."""

    url = reverse("api:practica")

    def _post(self, datos):
        cuerpo = datos if isinstance(datos, str) else json.dumps(datos)
        return self.client.post(self.url, cuerpo, content_type="application/json")

    def test_guarda_sesion_y_calcula_en_el_servidor(self):
        """Guarda duración, porcentaje (calculado aquí) y cantidad de análisis."""
        respuesta = self._post({"duracion": 60, "cantidad_analisis": 40, "amables": 34, "predominante": "enojo"})
        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["porcentaje"], 85.0)
        self.assertEqual(datos["nivel"], "excelente")
        self.assertEqual(datos["mensaje"], "¡Excelente actitud!")
        self.assertEqual(len(datos["consejos"]), 3)
        sesion = SesionPractica.objects.get(pk=datos["id"])
        self.assertEqual((sesion.duracion, sesion.porcentaje_amable, sesion.cantidad_analisis), (60, 85.0, 40))
        self.assertIsNotNone(sesion.fecha)

    def test_mensajes_por_umbral(self):
        """El mensaje cambia según el porcentaje: 60 % → bueno, 30 % → mejorar."""
        bueno = self._post({"duracion": 60, "cantidad_analisis": 10, "amables": 6})
        mejorar = self._post({"duracion": 60, "cantidad_analisis": 10, "amables": 3})
        self.assertEqual(bueno.json()["mensaje"], "Buen trabajo, sigue practicando")
        self.assertEqual(mejorar.json()["mensaje"], "Intenta mantener una expresión más amable")
        self.assertEqual(SesionPractica.objects.count(), 2)

    def test_sin_analisis_no_se_guarda(self):
        """Una sesión sin análisis con rostro responde 400 y no se guarda."""
        respuesta = self._post({"duracion": 60, "cantidad_analisis": 0, "amables": 0})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "datos_invalidos")
        self.assertEqual(SesionPractica.objects.count(), 0)

    def test_json_invalido(self):
        """Un cuerpo que no es JSON responde 400 json_invalido."""
        respuesta = self._post("{no es json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "json_invalido")

    def test_get_no_permitido(self):
        """GET responde 405."""
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_str_y_admin(self):
        """__str__ legible y admin de solo lectura con la columna de nivel."""
        from django.contrib.auth import get_user_model

        sesion = SesionPractica.objects.create(duracion=60, porcentaje_amable=72.5, cantidad_analisis=80)
        self.assertEqual(str(sesion), "Sesión de 60 s · 72.5 % amable")
        admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "clave-segura-123")
        self.client.force_login(admin)
        listado = self.client.get(reverse("admin:detector_sesionpractica_changelist"))
        self.assertEqual(listado.status_code, 200)
        self.assertContains(listado, "bueno")
        self.assertEqual(self.client.get(reverse("admin:detector_sesionpractica_add")).status_code, 403)


class EntrenadorPaginaTests(TestCase):
    """Elementos del entrenador: consejo de atención y medidor."""

    def setUp(self):
        self.respuesta = self.client.get(reverse("detector:index"))

    def test_titulo_y_tarjeta_de_consejo(self):
        """La página se titula 'Entrenador' e incluye la tarjeta 'Consejo de atención'."""
        self.assertContains(self.respuesta, "<title>Entrenador · EmoSense</title>", html=False)
        self.assertContains(self.respuesta, 'id="consejo-atencion"')
        self.assertContains(self.respuesta, "Consejo de atención")

    def test_medidor(self):
        """Botón del medidor, configuración en json_script y script medidor.js."""
        self.assertContains(self.respuesta, "Practicar atención (60 s)")
        self.assertContains(self.respuesta, '<script id="datos-practica" type="application/json">')
        self.assertContains(self.respuesta, "js/medidor.js")
        practica = self.respuesta.context["practica"]
        self.assertEqual(practica["url"], reverse("api:practica"))
        self.assertEqual(practica["duracion"], 60)
        self.assertEqual((practica["umbral_excelente"], practica["umbral_bueno"]), (80, 50))
        self.assertEqual(practica["emociones_amables"], ["alegria", "neutral"])


# --- API de análisis ---------------------------------------------------------


def _modelos_disponibles():
    """Indica si los archivos de los modelos están descargados."""
    try:
        verificar_archivos()
    except ModelosNoDisponiblesError:
        return False
    return True


def _archivo(nombre, datos, tipo="image/jpeg"):
    """Crea un archivo subido en memoria para el campo 'imagen'."""
    return SimpleUploadedFile(nombre, datos, content_type=tipo)


# Resultado falso de analizar_imagen con un rostro.
RESULTADO_CON_ROSTRO = {
    "ok": True,
    "ancho": 640,
    "alto": 480,
    "cantidad_rostros": 1,
    "rostros": [],
    "principal": {
        "x": 1, "y": 1, "w": 100, "h": 100, "confianza": 0.9,
        "emocion": "alegria", "puntuacion": 0.8,
        "puntuaciones": [{"emocion": "alegria", "puntuacion": 0.8}],
    },
    "calidad": {},
    "tiempo_ms": 12.5,
}


class ApiValidacionTests(TestCase):
    """Validaciones de /api/analizar/ y /api/foto/."""

    URLS = ("api:analizar", "api:foto")

    def assertError(self, respuesta, estado, codigo):
        """Comprueba el formato {ok:false, codigo, mensaje} de un error."""
        self.assertEqual(respuesta.status_code, estado)
        datos = respuesta.json()
        self.assertFalse(datos["ok"])
        self.assertEqual(datos["codigo"], codigo)
        self.assertTrue(datos["mensaje"])

    def test_sin_imagen(self):
        """Sin el campo 'imagen' debe responder 400 sin_imagen."""
        for nombre in self.URLS:
            with self.subTest(url=nombre):
                self.assertError(self.client.post(reverse(nombre)), 400, "sin_imagen")
        self.assertEqual(Analisis.objects.count(), 0)

    def test_formato_no_permitido(self):
        """Una foto GIF debe responder 415 formato."""
        gif = _archivo("animacion.gif", b"GIF89a" + b"\x00" * 100, "image/gif")
        respuesta = self.client.post(reverse("api:foto"), {"imagen": gif})
        self.assertError(respuesta, 415, "formato")

    def test_formato_falso_por_extension(self):
        """Un archivo de texto renombrado a .jpg también debe rechazarse."""
        falso = _archivo("foto.jpg", b"no soy una imagen")
        respuesta = self.client.post(reverse("api:foto"), {"imagen": falso})
        self.assertError(respuesta, 415, "formato")

    def test_mayor_a_2mb(self):
        """Un archivo de más de 2 MB debe responder 413 muy_grande."""
        grande = b"\xff\xd8\xff" + b"\x00" * (2 * 1024 * 1024)
        for nombre in self.URLS:
            with self.subTest(url=nombre):
                respuesta = self.client.post(reverse(nombre), {"imagen": _archivo("g.jpg", grande)})
                self.assertError(respuesta, 413, "muy_grande")

    def test_peticion_mayor_a_3mb(self):
        """Una petición de más de 3 MB se rechaza antes de leer el archivo."""
        enorme = b"\xff\xd8\xff" + b"\x00" * (4 * 1024 * 1024)
        respuesta = self.client.post(reverse("api:foto"), {"imagen": _archivo("e.jpg", enorme)})
        self.assertError(respuesta, 413, "muy_grande")

    def test_get_no_permitido(self):
        """GET debe responder 405."""
        for nombre in self.URLS:
            with self.subTest(url=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 405)

    def test_imagen_invalida(self):
        """Bytes que no son imagen en la cámara deben responder 400 imagen_invalida."""
        respuesta = self.client.post(
            reverse("api:analizar"), {"imagen": _archivo("f.jpg", b"\xff\xd8\xffbasura")}
        )
        self.assertError(respuesta, 400, "imagen_invalida")

    @mock.patch("detector.views.analizar_imagen", side_effect=ModelosNoDisponiblesError("x"))
    def test_sin_modelos_503(self, _analizar):
        """Si faltan los modelos debe responder 503 sin_modelos."""
        jpeg = _jpeg(np.zeros((50, 50, 3), np.uint8))
        respuesta = self.client.post(reverse("api:foto"), {"imagen": _archivo("n.jpg", jpeg)})
        self.assertError(respuesta, 503, "sin_modelos")


@mock.patch("detector.views.analizar_imagen", return_value=RESULTADO_CON_ROSTRO)
class ApiRegistroTests(TestCase):
    """Registro anónimo de resultados (con analizar_imagen simulado)."""

    def setUp(self):
        self.jpeg = _jpeg(np.zeros((50, 50, 3), np.uint8))

    def _post(self, nombre):
        return self.client.post(reverse(nombre), {"imagen": _archivo("f.jpg", self.jpeg)})

    def test_foto_se_registra_siempre(self, _analizar):
        """Cada foto genera un registro anónimo con el rostro principal."""
        self._post("api:foto")
        self._post("api:foto")
        self.assertEqual(Analisis.objects.filter(fuente="foto").count(), 2)
        registro = Analisis.objects.first()
        self.assertEqual(registro.emocion_principal, "alegria")
        self.assertEqual(registro.puntuacion, 0.8)

    def test_camara_maximo_uno_cada_5_segundos(self, _analizar):
        """Varios fotogramas seguidos de la misma sesión generan un solo registro."""
        for _ in range(3):
            self.assertEqual(self._post("api:analizar").status_code, 200)
        self.assertEqual(Analisis.objects.filter(fuente="camara").count(), 1)

        # Simula que pasaron más de 5 segundos desde el último registro.
        sesion = self.client.session
        sesion[servicios.CLAVE_SESION_CAMARA] -= servicios.INTERVALO_REGISTRO_CAMARA + 1
        sesion.save()
        self._post("api:analizar")
        self.assertEqual(Analisis.objects.filter(fuente="camara").count(), 2)

    def test_camara_sin_rostro_no_se_registra(self, analizar):
        """Los fotogramas de cámara sin rostro no se registran."""
        analizar.return_value = {**RESULTADO_CON_ROSTRO, "cantidad_rostros": 0, "principal": None}
        self._post("api:analizar")
        self.assertEqual(Analisis.objects.count(), 0)


@unittest.skipUnless(_modelos_disponibles(), "Faltan los modelos: ejecute python descargar_modelos.py")
class ApiModelosRealesTests(TestCase):
    """Pruebas con los modelos reales de OpenCV."""

    def test_imagen_negra_sin_rostros(self):
        """Una imagen negra no debe tener rostros y la foto se registra igual."""
        negra = _jpeg(np.zeros((480, 640, 3), np.uint8))
        respuesta = self.client.post(reverse("api:foto"), {"imagen": _archivo("negra.jpg", negra)})
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["cantidad_rostros"], 0)
        self.assertIsNone(datos["principal"])
        registro = Analisis.objects.get()
        self.assertEqual((registro.fuente, registro.cantidad_rostros, registro.emocion_principal), ("foto", 0, ""))


# --- Cobertura adicional ------------------------------------------------------


class CargadorTests(SimpleTestCase):
    """Carga de modelos cuando faltan los archivos."""

    def test_faltan_archivos(self):
        """Sin archivos, verificar y obtener lanzan ModelosNoDisponiblesError con la instrucción."""
        from detector.vision import cargador, config

        with tempfile.TemporaryDirectory() as carpeta, mock.patch.multiple(
            config,
            CARPETA_MODELOS=Path(carpeta),
            RUTA_PROTOTXT=Path(carpeta, "deploy.prototxt"),
            RUTA_CAFFEMODEL=Path(carpeta, "res10.caffemodel"),
            RUTA_FERPLUS=Path(carpeta, "ferplus.onnx"),
        ):
            cargador.obtener_modelos.cache_clear()
            try:
                with self.assertRaisesMessage(ModelosNoDisponiblesError, "Ejecute python descargar_modelos.py"):
                    cargador.verificar_archivos()
                with self.assertRaises(ModelosNoDisponiblesError):
                    cargador.obtener_modelos()
            finally:
                cargador.obtener_modelos.cache_clear()


class UtilidadesVisionTests(SimpleTestCase):
    """Decodificación, reducción y calidad."""

    def test_decodifica_png(self):
        """Los bytes PNG también se decodifican en memoria."""
        from detector.vision.analizador import decodificar_imagen

        _, png = cv2.imencode(".png", np.zeros((10, 20, 3), np.uint8))
        self.assertEqual(decodificar_imagen(png.tobytes()).shape, (10, 20, 3))

    def test_reducir_imagen(self):
        """Solo se reducen las imágenes cuyo lado mayor supera 640 px."""
        from detector.vision.analizador import reducir_imagen

        self.assertEqual(reducir_imagen(np.zeros((480, 640, 3), np.uint8))[1], 1.0)
        reducida, escala = reducir_imagen(np.zeros((1600, 1200, 3), np.uint8))
        self.assertEqual(reducida.shape[:2], (640, 480))
        self.assertAlmostEqual(escala, 0.4)

    def test_imagen_muy_brillante(self):
        """Una imagen casi blanca debe marcar brillo alto."""
        clara = np.full((240, 320, 3), 250, dtype=np.uint8)
        calidad = evaluar_calidad(clara, {"x": 100, "y": 60, "w": 100, "h": 100})
        self.assertEqual(calidad["brillo"]["estado"], "alto")

    def test_distancias(self):
        """Rostro pequeño = lejos ('bajo'); rostro enorme = cerca ('alto')."""
        imagen = np.full((480, 640, 3), 128, dtype=np.uint8)
        lejos = evaluar_calidad(imagen, {"x": 0, "y": 0, "w": 40, "h": 40})
        cerca = evaluar_calidad(imagen, {"x": 0, "y": 0, "w": 500, "h": 470})
        self.assertEqual(lejos["distancia"]["estado"], "bajo")
        self.assertEqual(cerca["distancia"]["estado"], "alto")


class FormatoTests(SimpleTestCase):
    """Detección del formato real por la firma del archivo."""

    def test_firmas(self):
        """Reconoce JPG, PNG y WebP; rechaza el resto."""
        self.assertEqual(servicios.detectar_formato(b"\xff\xd8\xff\xe0resto"), "jpg")
        self.assertEqual(servicios.detectar_formato(b"\x89PNG\r\n\x1a\nresto"), "png")
        self.assertEqual(servicios.detectar_formato(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "webp")
        self.assertIsNone(servicios.detectar_formato(b"GIF89a"))
        self.assertIsNone(servicios.detectar_formato(b""))


@mock.patch("detector.views.analizar_imagen", return_value=RESULTADO_CON_ROSTRO)
class ApiFormatosAceptadosTests(TestCase):
    """La API de fotos acepta PNG y WebP y rechaza archivos vacíos."""

    def _imagen(self, extension):
        _, datos = cv2.imencode(extension, np.full((40, 40, 3), 128, np.uint8))
        return datos.tobytes()

    def test_png_y_webp(self, _analizar):
        """Fotos PNG y WebP responden 200."""
        for extension, tipo in ((".png", "image/png"), (".webp", "image/webp")):
            with self.subTest(formato=extension):
                archivo = _archivo("foto" + extension, self._imagen(extension), tipo)
                respuesta = self.client.post(reverse("api:foto"), {"imagen": archivo})
                self.assertEqual(respuesta.status_code, 200)

    def test_archivo_vacio(self, _analizar):
        """Un archivo vacío responde 400 sin_imagen."""
        respuesta = self.client.post(reverse("api:foto"), {"imagen": _archivo("v.jpg", b"")})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["codigo"], "sin_imagen")


class AnalisisModeloYAdminTests(TestCase):
    """Representación del modelo y panel de administración."""

    def test_str(self):
        """__str__ muestra la fuente y la emoción (o 'sin rostro')."""
        con_rostro = Analisis.objects.create(
            fuente="camara", cantidad_rostros=1, emocion_principal="alegria", puntuacion=0.87
        )
        sin_rostro = Analisis.objects.create(fuente="foto", cantidad_rostros=0)
        self.assertEqual(str(con_rostro), "Cámara · Alegría (0.87)")
        self.assertEqual(str(sin_rostro), "Foto · sin rostro")

    def test_admin_solo_lectura(self):
        """El listado abre con filtros y no se permite agregar desde el admin."""
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "clave-segura-123")
        self.client.force_login(admin)
        Analisis.objects.create(fuente="foto", cantidad_rostros=0)
        listado = self.client.get(reverse("admin:detector_analisis_changelist"))
        self.assertEqual(listado.status_code, 200)
        self.assertContains(listado, "emocion_principal")  # filtro lateral
        self.assertEqual(self.client.get(reverse("admin:detector_analisis_add")).status_code, 403)
