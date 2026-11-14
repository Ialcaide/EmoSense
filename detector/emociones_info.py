"""
Información educativa de las 7 expresiones faciales básicas, orientada a la
atención al cliente.

``EMOCIONES`` es la única fuente de datos para el frontend. Cada emoción tiene:

- nombre, emoji, color y descripción;
- ``rol``: ``"propia"`` (la que el trabajador debe mostrar) o ``"cliente"``
  (la que debe aprender a reconocer en un cliente);
- ``consejo_atencion``: cómo actuar ante esa expresión;
- ``situacion``: un ejemplo de atención al público;
- ``guia``: cómo se ven cejas, ojos, nariz y boca.

Las claves coinciden con las que devuelve ``detector.vision`` (sin tilde).

Nota: EmoSense estima gestos visibles; no determina emociones reales.
"""

ROL_PROPIA = "propia"
ROL_CLIENTE = "cliente"

EMOCIONES = {
    "alegria": {
        "nombre": "Alegría",
        "emoji": "😄",
        "color": "#F5B700",
        "rol": ROL_PROPIA,
        "descripcion": "Sonrisa amplia con las mejillas elevadas y los ojos ligeramente entrecerrados.",
        "consejo_atencion": "Mantén una sonrisa natural al saludar y al despedir; que se note también en la mirada.",
        "situacion": "Un cliente entra al local y lo recibes en el mostrador.",
        "guia": {
            "cejas": "Relajadas, en su posición natural.",
            "ojos": "Ligeramente entrecerrados; pueden aparecer arrugas en las esquinas.",
            "nariz": "Relajada; las mejillas suben y se marcan los pliegues junto a ella.",
            "boca": "Comisuras hacia arriba y hacia atrás; puedes mostrar los dientes.",
        },
    },
    "tristeza": {
        "nombre": "Tristeza",
        "emoji": "😢",
        "color": "#3B82F6",
        "rol": ROL_CLIENTE,
        "descripcion": "Cejas levantadas por dentro, mirada caída y comisuras de los labios hacia abajo.",
        "consejo_atencion": "Habla con un tono suave, muestra empatía y dale tiempo para expresarse.",
        "situacion": "En la farmacia, un cliente cuenta que compra medicinas para un familiar hospitalizado.",
        "guia": {
            "cejas": "Levanta y junta la parte interna, formando una «V» invertida.",
            "ojos": "Párpados superiores algo caídos; mirada hacia abajo.",
            "nariz": "Relajada.",
            "boca": "Comisuras hacia abajo; el labio inferior puede sobresalir un poco.",
        },
    },
    "enojo": {
        "nombre": "Enojo",
        "emoji": "😠",
        "color": "#E5484D",
        "rol": ROL_CLIENTE,
        "descripcion": "Ceño fruncido, mirada fija y labios apretados.",
        "consejo_atencion": "Mantén la calma, escucha sin interrumpir y ofrece una solución concreta.",
        "situacion": "Un cliente reclama porque su pedido llegó tarde.",
        "guia": {
            "cejas": "Bájalas y júntalas, marcando líneas verticales entre ellas.",
            "ojos": "Mirada fija e intensa; párpados tensos.",
            "nariz": "Las fosas nasales pueden ensancharse.",
            "boca": "Labios apretados entre sí o tensos y entreabiertos.",
        },
    },
    "sorpresa": {
        "nombre": "Sorpresa",
        "emoji": "😮",
        "color": "#F97316",
        "rol": ROL_CLIENTE,
        "descripcion": "Cejas muy levantadas, ojos bien abiertos y boca abierta.",
        "consejo_atencion": "Aclara la información con calma y averigua si la sorpresa es buena o mala antes de seguir.",
        "situacion": "Un cliente ve que el total de su cuenta es mayor de lo que esperaba.",
        "guia": {
            "cejas": "Levántalas bien alto y curvadas; aparecen arrugas en la frente.",
            "ojos": "Muy abiertos; se ve el blanco por encima del iris.",
            "nariz": "Relajada.",
            "boca": "Abierta y relajada, con la mandíbula caída.",
        },
    },
    "miedo": {
        "nombre": "Miedo",
        "emoji": "😨",
        "color": "#8B5CF6",
        "rol": ROL_CLIENTE,
        "descripcion": "Cejas levantadas y juntas, ojos muy abiertos y labios estirados hacia los lados.",
        "consejo_atencion": "Explica cada paso con calma y palabras sencillas, y confirma que te entendió.",
        "situacion": "En el laboratorio, un paciente espera nervioso a que le tomen una muestra de sangre.",
        "guia": {
            "cejas": "Levántalas y júntalas a la vez; la frente se arruga en el centro.",
            "ojos": "Muy abiertos y tensos; párpados inferiores tensos.",
            "nariz": "Relajada o con las fosas algo dilatadas.",
            "boca": "Entreabierta, con los labios estirados horizontalmente hacia atrás.",
        },
    },
    "disgusto": {
        "nombre": "Disgusto",
        "emoji": "🤢",
        "color": "#22A06B",
        "rol": ROL_CLIENTE,
        "descripcion": "Nariz arrugada y labio superior levantado.",
        "consejo_atencion": "No lo tomes como algo personal: reconoce el problema y ofrece un cambio o una alternativa.",
        "situacion": "En el restaurante, un comensal nota que su plato llegó frío.",
        "guia": {
            "cejas": "Ligeramente bajadas.",
            "ojos": "Algo entrecerrados por la subida de las mejillas.",
            "nariz": "Arrúgala, como ante un mal olor.",
            "boca": "Levanta el labio superior; las comisuras pueden bajar.",
        },
    },
    "neutral": {
        "nombre": "Neutral",
        "emoji": "😐",
        "color": "#8A94A6",
        "rol": ROL_PROPIA,
        "descripcion": "Rostro relajado, sin tensión visible en ningún músculo.",
        "consejo_atencion": "Mientras el cliente habla, mantén un rostro sereno y atento, y asiente de vez en cuando.",
        "situacion": "Un cliente te explica con detalle lo que necesita.",
        "guia": {
            "cejas": "En su posición natural, sin levantarlas ni fruncirlas.",
            "ojos": "Abiertos con normalidad, mirando al frente.",
            "nariz": "Relajada.",
            "boca": "Cerrada o apenas entreabierta, sin sonreír.",
        },
    },
}

# Orden en el que se muestran las emociones en la interfaz.
ORDEN_EMOCIONES = tuple(EMOCIONES)

# Grupos de la guía de expresiones, en orden.
GRUPOS_GUIA = (
    {"rol": ROL_PROPIA, "titulo": "Expresiones que debes mostrar", "emoji": "🙂",
     "descripcion": "Las que el cliente debería ver en ti: amable al saludar y atenta mientras te habla."},
    {"rol": ROL_CLIENTE, "titulo": "Expresiones del cliente que debes reconocer", "emoji": "👀",
     "descripcion": "Aprende a identificarlas y a saber cómo responder a cada una."},
)

# Partes del rostro que muestra la guía, en orden: (clave en "guia", emoji, etiqueta).
PARTES_GUIA = (
    ("cejas", "🤨", "Cejas"),
    ("ojos", "👀", "Ojos"),
    ("nariz", "👃", "Nariz"),
    ("boca", "👄", "Boca"),
)

# Buenas prácticas de atención al cliente.
BUENAS_PRACTICAS = (
    {"emoji": "👁️", "titulo": "Contacto visual", "texto": "Mira al cliente mientras habla; demuestra que tienes toda tu atención."},
    {"emoji": "😊", "titulo": "Sonrisa natural", "texto": "Sonríe al saludar y al despedir, sin exagerar ni forzar el gesto."},
    {"emoji": "🧍", "titulo": "Postura", "texto": "Mantente erguido, con los hombros relajados y los brazos sin cruzar."},
    {"emoji": "🗣️", "titulo": "Tono de voz", "texto": "Habla claro, a un ritmo pausado y con un tono amable, incluso si el cliente está molesto."},
)

# Consejos generales para que la cámara capte bien el rostro.
CONSEJOS_CAMARA = (
    {"emoji": "💡", "titulo": "Luz frontal", "texto": "Ilumina tu rostro de frente; evita tener una ventana o lámpara detrás."},
    {"emoji": "🎯", "titulo": "Rostro centrado", "texto": "Colócate en el centro de la imagen, a unos 50 cm de la cámara."},
    {"emoji": "🧢", "titulo": "Rostro despejado", "texto": "Quítate la gorra y los lentes oscuros para que se vean cejas y ojos."},
    {"emoji": "🎭", "titulo": "Exagera un poco", "texto": "Marca el gesto un poco más de lo normal; el modelo lo reconoce mejor."},
)


def emociones_por_rol(rol):
    """Devuelve las claves de las emociones con el rol indicado, en orden."""
    return [clave for clave, info in EMOCIONES.items() if info["rol"] == rol]


def guia_expresiones():
    """Prepara los datos de la guía de expresiones para la plantilla.

    Returns:
        Lista de grupos (ver ``GRUPOS_GUIA``), cada uno con la clave
        ``emociones``: lista de ``{clave, nombre, emoji, color, rol,
        consejo_atencion, situacion, filas}``, donde ``filas`` es
        ``[{emoji, parte, texto}]`` con las partes de ``PARTES_GUIA``.
    """
    grupos = []
    for grupo in GRUPOS_GUIA:
        tarjetas = [
            {
                "clave": clave,
                "nombre": info["nombre"],
                "emoji": info["emoji"],
                "color": info["color"],
                "rol": info["rol"],
                "consejo_atencion": info["consejo_atencion"],
                "situacion": info["situacion"],
                "filas": [
                    {"emoji": emoji, "parte": etiqueta, "texto": info["guia"][parte]}
                    for parte, emoji, etiqueta in PARTES_GUIA
                ],
            }
            for clave, info in EMOCIONES.items()
            if info["rol"] == grupo["rol"]
        ]
        grupos.append({**grupo, "emociones": tarjetas})
    return grupos


def emociones_para_frontend():
    """Devuelve una copia de EMOCIONES lista para enviar al navegador.

    Si existe ``static/gifs/<clave>.gif`` se agrega la clave ``gif`` con su URL;
    si no existe, la interfaz muestra solo el emoji.
    """
    from django.contrib.staticfiles import finders
    from django.templatetags.static import static

    datos = {}
    for clave, info in EMOCIONES.items():
        copia = dict(info)
        ruta = f"gifs/{clave}.gif"
        if finders.find(ruta):
            copia["gif"] = static(ruta)
        datos[clave] = copia
    return datos
