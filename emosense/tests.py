"""Pruebas de la página de inicio, la plantilla base y descargar_modelos.py."""

import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class InicioTests(TestCase):
    """Verifica que la página de inicio responda y use la plantilla base."""

    def test_inicio_responde_200(self):
        """La ruta '/' debe responder con código 200."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(respuesta.status_code, 200)

    def test_inicio_usa_plantillas(self):
        """La página de inicio debe heredar de base.html."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertTemplateUsed(respuesta, "inicio.html")
        self.assertTemplateUsed(respuesta, "base.html")

    def test_base_contiene_aviso_y_footer(self):
        """El footer debe incluir el crédito del curso y el aviso educativo."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "EmoSense – UNEMI – Construcción de Software 2026")
        self.assertContains(respuesta, "Estima gestos visibles; no determina emociones reales.")

    def test_enlace_activo_marcado(self):
        """El enlace de la sección actual debe tener aria-current='page'."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'aria-current="page"', count=1)

    def test_hero(self):
        """El hero tiene el título de atención al cliente, los 7 chips en 2 grupos y los botones."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "Tu expresión también atiende.")
        self.assertContains(respuesta, "Entrénala con EmoSense.")
        self.assertContains(respuesta, 'class="chip chip--', count=7)
        self.assertContains(respuesta, "Tú muestras")
        self.assertContains(respuesta, "Tu cliente puede mostrar")
        self.assertContains(respuesta, f'href="{reverse("detector:index")}">Comenzar entrenamiento</a>')
        self.assertContains(respuesta, f'href="{reverse("detector:index")}#guia">Ver guía de atención</a>')

    def test_sin_modo_reto(self):
        """El modo reto ya no existe: ni enlaces ni ruta."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertNotContains(respuesta, "Modo reto")
        self.assertNotContains(respuesta, "/retos/")
        self.assertEqual(self.client.get("/retos/").status_code, 404)

    def test_navegacion(self):
        """La barra tiene Inicio · Entrenador · Guía de atención (ancla a la guía)."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, f'href="{reverse("detector:index")}">Entrenador</a>')
        self.assertContains(respuesta, f'href="{reverse("detector:index")}#guia">Guía de atención</a>')

    def test_secciones(self):
        """Incluye '¿Para quién es?', 'Cómo funciona', 'Tu privacidad' y limitaciones."""
        respuesta = self.client.get(reverse("inicio"))
        for texto in ("¿Para quién es?", "Recepcionistas", "Vendedores", "Meseros", "Personal de salud",
                      "Cómo funciona", "Mide tu amabilidad",
                      "Tu privacidad", "Sin registro", "Sin guardar fotos", "Análisis local",
                      "Limitaciones", "evaluar el"):
            with self.subTest(texto=texto):
                self.assertContains(respuesta, texto)

    def test_logo_y_pantalla_carga(self):
        """El logo SVG se usa en barra, hero y pantalla de carga, que se muestra al inicio."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertTemplateUsed(respuesta, "partials/logo.html")
        self.assertContains(respuesta, 'class="logo__guino"', count=3)
        self.assertContains(respuesta, 'aria-live="polite" data-inicial')


class DescargarModelosTests(SimpleTestCase):
    """Script descargar_modelos.py (sin usar la red)."""

    def test_omite_archivos_existentes(self):
        """Si el archivo ya existe y no está vacío, no se descarga."""
        import descargar_modelos

        with tempfile.TemporaryDirectory() as carpeta:
            Path(carpeta, "deploy.prototxt").write_text("contenido")
            with mock.patch("urllib.request.urlretrieve") as descarga, mock.patch("sys.stdout"):
                resultado = descargar_modelos.descargar_modelo("deploy.prototxt", "https://ejemplo", Path(carpeta))
            self.assertFalse(resultado)
            descarga.assert_not_called()

    def test_descarga_y_renombra(self):
        """Descarga a un archivo .part y lo renombra al terminar."""
        import descargar_modelos

        def descarga_falsa(url, destino, reporthook=None):
            Path(destino).write_bytes(b"modelo")
            reporthook(1, 6, 6)

        with tempfile.TemporaryDirectory() as carpeta:
            with mock.patch("urllib.request.urlretrieve", side_effect=descarga_falsa), mock.patch("sys.stdout"):
                self.assertTrue(descargar_modelos.descargar_modelo("m.onnx", "https://ejemplo", Path(carpeta)))
            self.assertEqual(Path(carpeta, "m.onnx").read_bytes(), b"modelo")
            self.assertFalse(Path(carpeta, "m.onnx.part").exists())

    def test_error_no_deja_archivos_incompletos(self):
        """Si la descarga falla, se borra el .part y main() devuelve 1."""
        import descargar_modelos

        def descarga_fallida(url, destino, reporthook=None):
            Path(destino).write_bytes(b"incompleto")
            raise OSError("sin conexión")

        with tempfile.TemporaryDirectory() as carpeta:
            with mock.patch("urllib.request.urlretrieve", side_effect=descarga_fallida), \
                    mock.patch.object(descargar_modelos, "CARPETA_MODELOS", Path(carpeta)), \
                    mock.patch("sys.stdout"):
                with self.assertRaises(OSError):
                    descargar_modelos.descargar_modelo("m.onnx", "https://ejemplo", Path(carpeta))
                self.assertEqual(list(Path(carpeta).iterdir()), [])
                self.assertEqual(descargar_modelos.main(), 1)
