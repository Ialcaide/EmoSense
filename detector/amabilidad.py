"""
Medidor de amabilidad (funciones puras, sin Django).

Durante una sesión de práctica de 60 s se cuenta en qué porcentaje de los
análisis con rostro la expresión principal fue amable (alegría o neutral).
Los análisis sin rostro no cuentan. El navegador envía los conteos y el
servidor calcula el porcentaje, el nivel, el mensaje y los consejos.
"""

from .emociones_info import EMOCIONES, ROL_PROPIA

# Duración de una sesión de práctica (segundos).
DURACION_PRACTICA = 60

# Expresiones que cuentan como amables: las de rol "propia".
EMOCIONES_AMABLES = tuple(clave for clave, info in EMOCIONES.items() if info["rol"] == ROL_PROPIA)

# Umbrales de los niveles (porcentaje mínimo).
UMBRAL_EXCELENTE = 80
UMBRAL_BUENO = 50

# Límite de análisis aceptados en una sesión (uno cada ~0,5 s, con margen).
MAX_ANALISIS = 600

# Mensaje y 2 consejos fijos por nivel.
NIVELES = {
    "excelente": {
        "mensaje": "¡Excelente actitud!",
        "consejos": [
            "Mantén esta expresión también en los momentos de más trabajo.",
            "Combina la sonrisa con contacto visual y un saludo por el nombre cuando puedas.",
        ],
    },
    "bueno": {
        "mensaje": "Buen trabajo, sigue practicando",
        "consejos": [
            "Vuelve a una expresión neutral y serena cuando el cliente te esté explicando algo.",
            "Sonríe de forma natural al saludar y al despedir, aunque estés ocupado.",
        ],
    },
    "mejorar": {
        "mensaje": "Intenta mantener una expresión más amable",
        "consejos": [
            "Relaja la frente y la mandíbula antes de atender; respira hondo una vez.",
            "Practica frente a la cámara una sonrisa suave y una expresión neutral atenta.",
        ],
    },
}

# Tercer consejo según la expresión no amable que más apareció.
CONSEJO_POR_EXPRESION = {
    "enojo": "Se notó el ceño fruncido: relaja el entrecejo y suelta la mandíbula.",
    "tristeza": "Se notó una expresión caída: levanta un poco las comisuras y la mirada.",
    "miedo": "Se notó tensión en la mirada: relaja los párpados y respira con calma.",
    "disgusto": "Se notó la nariz arrugada: relaja la nariz y el labio superior.",
    "sorpresa": "Se notaron las cejas muy levantadas: déjalas en su posición natural.",
}
CONSEJO_SIN_PREDOMINANTE = "Casi no hubo expresiones de tensión: sigue alternando sonrisa y neutral atenta."


def es_amable(emocion):
    """Indica si una expresión cuenta como amable (alegría o neutral)."""
    return emocion in EMOCIONES_AMABLES


def calcular_porcentaje(amables, total):
    """Porcentaje de análisis amables sobre el total, redondeado a 1 decimal.

    Raises:
        ValueError: si ``total`` es 0 (no hubo análisis con rostro).
    """
    if total <= 0:
        raise ValueError("No hubo análisis con rostro en la sesión.")
    return round(amables * 100 / total, 1)


def nivel_por_porcentaje(porcentaje):
    """Devuelve 'excelente' (≥80), 'bueno' (50–79) o 'mejorar' (<50)."""
    if porcentaje >= UMBRAL_EXCELENTE:
        return "excelente"
    if porcentaje >= UMBRAL_BUENO:
        return "bueno"
    return "mejorar"


def evaluar_sesion(porcentaje, predominante=None):
    """Devuelve el resultado de una sesión: nivel, mensaje y 3 consejos.

    Args:
        porcentaje: porcentaje de análisis amables.
        predominante: expresión no amable más frecuente, o ``None``.

    Returns:
        ``{nivel, mensaje, consejos}`` con 2 consejos fijos del nivel y
        1 según la expresión predominante.
    """
    nivel = nivel_por_porcentaje(porcentaje)
    extra = CONSEJO_POR_EXPRESION.get(predominante, CONSEJO_SIN_PREDOMINANTE)
    return {
        "nivel": nivel,
        "mensaje": NIVELES[nivel]["mensaje"],
        "consejos": [*NIVELES[nivel]["consejos"], extra],
    }


def _entero(datos, campo, minimo, maximo):
    """Lee un entero de ``datos`` y comprueba que esté en [minimo, maximo]."""
    valor = datos.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"'{campo}' debe ser un número entero.")
    if not minimo <= valor <= maximo:
        raise ValueError(f"'{campo}' debe estar entre {minimo} y {maximo}.")
    return valor


def validar_sesion(datos):
    """Valida los conteos de una sesión enviados por el navegador.

    Espera ``{duracion, cantidad_analisis, amables, predominante?}``.

    Returns:
        Diccionario limpio con esas claves (``predominante`` puede ser None).

    Raises:
        ValueError: con un mensaje en español si algún dato no es válido.
    """
    if not isinstance(datos, dict):
        raise ValueError("Se esperaba un objeto JSON.")
    duracion = _entero(datos, "duracion", 1, DURACION_PRACTICA)
    cantidad = _entero(datos, "cantidad_analisis", 1, MAX_ANALISIS)
    amables = _entero(datos, "amables", 0, cantidad)
    predominante = datos.get("predominante")
    if predominante is not None and predominante not in CONSEJO_POR_EXPRESION:
        raise ValueError("'predominante' debe ser una expresión no amable válida.")
    return {
        "duracion": duracion,
        "cantidad_analisis": cantidad,
        "amables": amables,
        "predominante": predominante,
    }
