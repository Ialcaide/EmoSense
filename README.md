<p align="center">
  <img src="static/img/logo.svg" alt="Logo de EmoSense" width="96" height="96">
</p>

<h1 align="center">EmoSense</h1>

<p align="center">
  <strong>Tu expresión también atiende. Entrénala con EmoSense.</strong><br>
  Entrenador de expresión facial para atención al cliente, con retroalimentación
  en tiempo real usando visión artificial.
</p>

<p align="center">
  UNEMI · Construcción de Software · Práctica 3 · 2026
</p>

---

## Descripción y objetivo educativo

EmoSense ayuda al personal de atención al público (recepción, ventas, restaurantes, farmacias y
laboratorios) a:

1. **Practicar las expresiones adecuadas frente al cliente**: una sonrisa natural al saludar y
   una expresión neutral y atenta mientras el cliente habla.
2. **Reconocer las expresiones de un cliente** (enojo, tristeza, miedo, disgusto y sorpresa) y
   saber cómo responder a cada una.

La cámara del navegador (o una foto) se analiza con OpenCV para **estimar qué expresión facial
visible** se parece más al gesto de la persona, y la aplicación responde con consejos de atención,
un medidor de amabilidad y una guía práctica.

> ⚠️ EmoSense **estima gestos visibles; no diagnostica ni determina emociones reales**. Es una
> herramienta de práctica personal y no debe usarse para evaluar el desempeño de trabajadores.

## Funcionalidades

- **Entrenador en vivo** (`/detector/`): analiza la cámara cada ~500 ms y dibuja un recuadro con
  la expresión estimada sobre cada rostro.
- **Consejo de atención**: según la expresión detectada, el panel muestra:
  - para alegría y neutral (*expresiones propias*): cómo usarlas frente al cliente;
  - para las otras 5 (*expresiones del cliente*): cómo responder, con una situación de ejemplo.
- **Medidor de amabilidad (60 s)**: la práctica principal. Mide en qué porcentaje de los análisis
  con rostro mostraste una expresión amable (alegría o neutral) y responde con:
  - ≥ 80 %: «¡Excelente actitud!»; 50–79 %: «Buen trabajo, sigue practicando»;
    < 50 %: «Intenta mantener una expresión más amable»;
  - 3 consejos de mejora: 2 según el nivel y 1 según la expresión no amable que más apareció;
  - un historial con tus últimas 5 sesiones, guardado solo en tu navegador.
- **Análisis de fotos** JPG, PNG o WebP (máx. 2 MB), con vista previa y recuadros.
- **Panel de resultados**: emoji animado, barras con las 7 puntuaciones, rostros detectados,
  tiempo de análisis y recomendaciones de luz, nitidez y distancia.
- **Guía de atención** (desplegable, también accesible desde el menú):
  - «Expresiones que debes mostrar» (alegría, neutral);
  - «Expresiones del cliente que debes reconocer» (las otras 5), cada una con su consejo y
    una situación de ejemplo;
  - «Buenas prácticas» (contacto visual, sonrisa natural, postura y tono de voz) y consejos
    para la cámara.
- **Tema claro/oscuro**, diseño responsive (mobile-first) y accesibilidad (contraste AA, foco
  visible, `aria-label`, respeto de `prefers-reduced-motion`).
- **Panel de administración** de solo lectura con los análisis y las sesiones de práctica anónimas.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.10+ · Django 5.2 |
| Visión artificial | OpenCV 4.x (`opencv-python-headless`) · NumPy |
| Detección de rostros | Res10 SSD (Caffe) con `cv2.dnn.readNetFromCaffe` |
| Expresiones | FER+ (ONNX) con `cv2.dnn.readNetFromONNX` |
| Base de datos | PostgreSQL (con `psycopg` 3) |
| Configuración | `python-dotenv` (archivo `.env`) |
| Frontend | Plantillas de Django + HTML, CSS y JavaScript propios (sin frameworks) |

> Se usa **OpenCV < 5**, porque OpenCV 5 eliminó `readNetFromCaffe`.

## Arquitectura

```
EmoSense/
├── manage.py
├── descargar_modelos.py      # Descarga los 3 modelos a modelos_ia/
├── requirements.txt
├── .env.example              # Plantilla de variables de entorno
├── emosense/                 # Proyecto Django: settings, urls, vista de inicio
├── detector/                 # App del entrenador
│   ├── vision/               # Módulo de visión (solo OpenCV)
│   │   ├── config.py         #   rutas de modelos y umbrales
│   │   ├── cargador.py       #   carga Res10 y FER+ una sola vez (CPU)
│   │   ├── rostros.py        #   detección de rostros (Res10 SSD)
│   │   ├── emociones.py      #   clasificación FER+ (7 clases + softmax)
│   │   ├── calidad.py        #   brillo, nitidez y distancia
│   │   ├── analizador.py     #   flujo completo: bytes → resultado
│   │   └── errores.py
│   ├── emociones_info.py     # Datos de atención: rol, consejo, situación, guía, buenas prácticas
│   ├── amabilidad.py         # Reglas del medidor: umbrales, mensajes, consejos, validación
│   ├── servicios.py          # Validación de imágenes y registro anónimo
│   ├── models.py             # Analisis, SesionPractica
│   ├── views.py              # Página del entrenador y APIs
│   └── templates/detector/   # index.html, _medidor.html, _guia.html
├── templates/                # base.html, inicio.html, partials/logo.html
├── static/
│   ├── css/                  # tokens, base, camara, detector, inicio
│   ├── js/                   # tema, camara (cámara y análisis), medidor, detector
│   ├── img/logo.svg
│   └── gifs/                 # GIF opcionales por emoción (<clave>.gif)
└── modelos_ia/               # Modelos descargados (ignorados por git)
```

**Flujo de un análisis**

1. El navegador captura un fotograma con `getUserMedia`, lo reduce a 640 px y lo envía como JPEG
   a `POST /api/analizar/` (o `POST /api/foto/` para fotos).
2. Django valida el archivo y lo decodifica **en memoria** con `cv2.imdecode`.
3. Res10 SSD detecta los rostros; FER+ clasifica cada uno (rostro en gris, 64×64).
4. Se descarta la clase *contempt*, se aplica softmax a las 7 restantes y se evalúa la calidad.
5. La API responde en JSON y solo se guarda un resultado anónimo en PostgreSQL.

**Flujo del medidor de amabilidad**

1. Durante 60 s el navegador cuenta los análisis con rostro y cuántos fueron alegría o neutral.
2. Al terminar envía los conteos a `POST /api/practica/`; el servidor valida los datos, calcula
   el porcentaje, guarda una `SesionPractica` anónima y devuelve el mensaje y los consejos.
3. Si no hubo ningún rostro o la sesión se canceló, no se envía ni se guarda nada.

**Endpoints**

| Método y ruta | Uso |
|---|---|
| `POST /api/analizar/` | Fotograma de la cámara (campo `imagen`) |
| `POST /api/foto/` | Foto JPG, PNG o WebP (campo `imagen`) |
| `POST /api/practica/` | Sesión del medidor: `{"duracion", "cantidad_analisis", "amables", "predominante"}` |

Los errores responden `{"ok": false, "codigo": "...", "mensaje": "..."}` con los códigos
`sin_imagen`, `muy_grande`, `formato`, `imagen_invalida`, `sin_modelos` (503),
`json_invalido` y `datos_invalidos`.

## Requisitos

- Python **3.10 o superior** (probado con 3.14).
- PostgreSQL **14 o superior** (probado con 17).
- Git.
- Un navegador moderno (Chrome, Edge o Firefox) con cámara. La cámara solo funciona en
  `localhost`/`127.0.0.1` o con HTTPS.
- Conexión a internet la primera vez, para descargar los modelos (~44 MB).

## Instalación paso a paso

Los comandos están en **PowerShell (Windows)**; las diferencias para macOS/Linux se indican aparte.

### 1. Clonar el repositorio

```powershell
git clone https://github.com/TU_USUARIO/EmoSense.git
cd EmoSense
```

### 2. Crear y activar el entorno virtual

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

> Si PowerShell bloquea el script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
> macOS/Linux: `python3 -m venv venv` y `source venv/bin/activate`.

### 3. Instalar las dependencias

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Crear la base de datos en PostgreSQL

```powershell
psql -U postgres -c "CREATE DATABASE emosense ENCODING 'UTF8';"
```

> Si `psql` no se reconoce en Windows, usa la ruta completa, por ejemplo
> `& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE emosense ENCODING 'UTF8';"`,
> o crea la base `emosense` desde pgAdmin.

### 5. Configurar el archivo `.env`

```powershell
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Abre `.env`, pega la clave generada en `SECRET_KEY` y escribe tu contraseña de PostgreSQL en
`DB_PASSWORD`:

```ini
SECRET_KEY=la-clave-generada
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=emosense
DB_USER=postgres
DB_PASSWORD=tu_contrasena
DB_HOST=localhost
DB_PORT=5432
```

> macOS/Linux: `cp .env.example .env`.

### 6. Descargar los modelos de visión

```powershell
python descargar_modelos.py
```

Descarga `deploy.prototxt`, `res10_300x300_ssd_iter_140000.caffemodel` y `emotion-ferplus-8.onnx`
en `modelos_ia/`, muestra el progreso y omite los archivos que ya existan.

### 7. Crear las tablas

```powershell
python manage.py migrate
```

Opcional, para entrar al panel `/admin/`:

```powershell
python manage.py createsuperuser
```

### 8. Ejecutar el servidor

```powershell
python manage.py runserver
```

Abre **http://127.0.0.1:8000/**.

## Pruebas

```powershell
python manage.py test
```

Hay 78 pruebas que cubren el módulo de visión (con redes falsas, sin necesitar los modelos),
la API de análisis, el medidor de amabilidad (umbrales, consejos y validación), la API de práctica
y el modelo `SesionPractica`, los datos de atención al cliente, las páginas, el panel de
administración y el script de descarga. La prueba que usa los modelos reales se omite
automáticamente si no se han descargado.

> El usuario de PostgreSQL necesita permiso para crear bases de datos, porque Django crea una
> base temporal `test_emosense` (el usuario `postgres` ya lo tiene).

## Uso

### Entrenador (`/detector/`)

1. En la pestaña **📹 Cámara**, pulsa **Iniciar cámara** y acepta el permiso del navegador.
2. Verás un recuadro sobre tu rostro con la expresión estimada. El panel de la derecha muestra
   las 7 puntuaciones y la tarjeta **Consejo de atención**:
   - si muestras alegría o neutral, te dice cómo usar esa expresión con el cliente;
   - si imitas la expresión de un cliente (por ejemplo, enojo), te dice cómo responder y te da
     una situación de ejemplo.
3. Pulsa **Detener cámara** para liberar la cámara.
4. En la pestaña **🖼️ Foto**, elige o arrastra una imagen JPG, PNG o WebP de hasta 2 MB.

### Medidor de amabilidad

1. En la pestaña Cámara, pulsa **Practicar atención (60 s)**; si la cámara estaba apagada, se
   enciende sola.
2. Imagina que atiendes a un cliente durante 60 segundos. Verás la cuenta regresiva y el
   porcentaje amable en vivo.
3. Al terminar aparecen el porcentaje, el mensaje según el resultado y 3 consejos. La sesión se
   guarda de forma anónima y se agrega a **Tus últimas sesiones**.
4. **Cancelar práctica** o **Detener cámara** termina la sesión sin guardar nada.

### Guía de atención

Ábrela con **Guía de atención** en el menú o con **📖 Guía de atención** al final del entrenador.
Incluye las expresiones que debes mostrar, las del cliente que debes reconocer con su consejo,
las buenas prácticas y los consejos para la cámara.

### GIF opcionales

Si colocas archivos `static/gifs/<clave>.gif` (por ejemplo `alegria.gif`), se muestran en el
panel de resultados. Si no existen, se muestra solo el emoji.

## Privacidad

- **Sin registro**: no hay cuentas ni inicio de sesión.
- **Sin guardar imágenes ni video**: cada fotograma se procesa en memoria y se descarta.
  Django está configurado para no escribir las subidas en archivos temporales.
- **Análisis en el servidor de EmoSense**: el procesamiento se hace con OpenCV en el propio
  servidor; las imágenes no se envían a servicios externos.
- **Solo resultados anónimos** en PostgreSQL:
  - análisis: fuente (cámara/foto), cantidad de rostros, expresión principal, puntuaciones,
    tiempo y fecha (la cámara registra como máximo uno cada 5 segundos por sesión);
  - sesiones de práctica: duración, porcentaje amable, cantidad de análisis y fecha.
- **Historial local**: las últimas 5 sesiones (porcentaje y fecha) se guardan solo en el
  `localStorage` de tu navegador; puedes borrarlas con **Borrar historial**.

## Limitaciones

- Estima **gestos visibles**; un gesto no siempre refleja lo que una persona siente.
- El modelo puede equivocarse con poca luz, rostros de perfil, lentes oscuros, gorras,
  oclusiones o baja resolución, y con diferencias entre personas y culturas.
- Una expresión neutral o amable no garantiza una buena atención: el tono, las palabras y la
  solución que se ofrece importan tanto como el rostro.
- FER+ fue entrenado con imágenes de 48×48 en escala de grises; es un modelo ligero, no de
  última generación.
- **No debe usarse para evaluar, vigilar ni sancionar a trabajadores**, ni para juzgar a clientes.

## Guion de video (máx. 3 minutos)

Antes de grabar: modelos descargados, superusuario creado, buena luz y una terminal con
`python manage.py test` ya ejecutado.

| Tiempo | En pantalla | Narración |
|---|---|---|
| 0:00–0:20 | Inicio: pantalla de carga, logo guiñando, hero y «¿Para quién es?» | «EmoSense es un entrenador de expresión facial para atención al cliente: para recepcionistas, vendedores, meseros y personal de salud.» |
| 0:20–0:35 | Bajar por Cómo funciona, Privacidad y Limitaciones; pulsar 🌙 | «Usa visión artificial con OpenCV, no guarda fotos ni pide registro, y estima gestos visibles: no emociones reales ni evaluaciones de desempeño.» |
| 0:35–1:10 | Comenzar entrenamiento → Iniciar cámara; sonreír y luego poner cara neutral | «Al sonreír, el panel me dice cómo usar esa expresión con el cliente. Con una expresión neutral, me recuerda mantenerme atento mientras me hablan.» |
| 1:10–1:35 | Imitar enojo y luego tristeza | «Si imito a un cliente molesto, la tarjeta me dice cómo responder: mantener la calma, escuchar y ofrecer una solución, con una situación de ejemplo.» |
| 1:35–2:15 | Practicar atención (60 s): cuenta regresiva, porcentaje en vivo; al final, resultado, consejos e historial (acelerar en edición) | «El medidor de amabilidad es la práctica principal: durante 60 segundos mide qué porcentaje del tiempo mostré una expresión amable. Al final recibo un mensaje, tres consejos y el historial de mis últimas sesiones.» |
| 2:15–2:30 | Pestaña Foto: subir una foto con varias personas | «También puedo analizar fotos; el panel muestra el rostro más grande.» |
| 2:30–2:45 | Menú → Guía de atención: los dos grupos y Buenas prácticas | «La guía separa las expresiones que debo mostrar de las del cliente que debo reconocer, y resume las buenas prácticas.» |
| 2:45–3:00 | `/admin/` → Sesiones de práctica; terminal con `Ran 78 tests … OK` | «En el admin solo hay resultados anónimos. El proyecto tiene 78 pruebas automatizadas y usa Django, OpenCV y PostgreSQL. Gracias.» |

## Créditos de los modelos

- **Detector de rostros Res10 SSD** (`deploy.prototxt` y
  `res10_300x300_ssd_iter_140000.caffemodel`): modelo de ejemplo del módulo DNN de
  [OpenCV](https://github.com/opencv/opencv/tree/master/samples/dnn/face_detector),
  con pesos publicados en [opencv_3rdparty](https://github.com/opencv/opencv_3rdparty/tree/dnn_samples_face_detector_20170830).
- **FER+** (`emotion-ferplus-8.onnx`): modelo del
  [ONNX Model Zoo](https://github.com/onnx/models/tree/main/validated/vision/body_analysis/emotion_ferplus),
  basado en el conjunto de datos FER+ de Microsoft: E. Barsoum, C. Zhang, C. Canton Ferrer y
  Z. Zhang, *Training Deep Networks for Facial Expression Recognition with Crowd-Sourced Label
  Distribution*, ACM ICMI 2016.

Consulta las licencias en los repositorios de origen. Los modelos no se incluyen en este
repositorio; se descargan con `descargar_modelos.py`.

## Integrantes

[ESCRIBE AQUÍ LOS NOMBRES]
