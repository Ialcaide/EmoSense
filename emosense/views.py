"""Vistas generales del proyecto (páginas que no pertenecen a una app)."""

from django.shortcuts import render

from detector.emociones_info import EMOCIONES, ROL_CLIENTE, ROL_PROPIA

# Sección "¿Para quién es?".
PERFILES = (
    {
        "emoji": "🛎️",
        "titulo": "Recepcionistas",
        "texto": "Recibe a cada persona con una sonrisa natural y mantén la calma ante las esperas.",
    },
    {
        "emoji": "🛍️",
        "titulo": "Vendedores",
        "texto": "Transmite confianza y detecta a tiempo cuándo un cliente duda o se molesta.",
    },
    {
        "emoji": "🍽️",
        "titulo": "Meseros",
        "texto": "Atiende con amabilidad y reacciona bien cuando un plato no fue lo que el cliente esperaba.",
    },
    {
        "emoji": "🩺",
        "titulo": "Personal de salud",
        "texto": "En farmacias y laboratorios, reconoce la preocupación o el miedo y responde con empatía.",
    },
)

# Sección "Cómo funciona".
PASOS = (
    {
        "emoji": "📷",
        "titulo": "Practica",
        "texto": "Activa la cámara: OpenCV localiza tu rostro y el modelo FER+ estima tu expresión en tiempo real.",
    },
    {
        "emoji": "⏱️",
        "titulo": "Mide tu amabilidad",
        "texto": "Durante 60 segundos, el medidor calcula qué porcentaje del tiempo mostraste alegría o neutralidad.",
    },
    {
        "emoji": "💬",
        "titulo": "Aprende a responder",
        "texto": "Para cada expresión del cliente recibes un consejo de atención y una situación de ejemplo.",
    },
)

# Sección "Tu privacidad".
PRIVACIDAD = (
    {
        "emoji": "🙅",
        "titulo": "Sin registro",
        "texto": "No hay cuentas ni inicio de sesión: entras y practicas.",
    },
    {
        "emoji": "🗑️",
        "titulo": "Sin guardar fotos",
        "texto": "Las imágenes se analizan en memoria y se descartan; solo se guardan resultados anónimos.",
    },
    {
        "emoji": "🏠",
        "titulo": "Análisis local",
        "texto": "El análisis lo hace el propio servidor de EmoSense con OpenCV, sin enviar tu imagen a servicios externos.",
    },
)


def inicio(request):
    """Muestra la página de inicio: presentación, público, funcionamiento y privacidad."""
    def tarjetas(rol):
        return [{"clave": clave, **info} for clave, info in EMOCIONES.items() if info["rol"] == rol]

    contexto = {
        "propias": tarjetas(ROL_PROPIA),
        "del_cliente": tarjetas(ROL_CLIENTE),
        "perfiles": PERFILES,
        "pasos": PASOS,
        "privacidad": PRIVACIDAD,
    }
    return render(request, "inicio.html", contexto)
