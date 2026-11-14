"""
Configuración del proyecto EmoSense.

Los valores sensibles (SECRET_KEY, DEBUG y credenciales de la base de datos)
se leen desde el archivo ``.env`` ubicado en la raíz del proyecto.
Use ``.env.example`` como plantilla.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Ruta base del proyecto: BASE_DIR / "subcarpeta".
BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables del archivo .env (si existe) en os.environ.
load_dotenv(BASE_DIR / ".env")


def _env_bool(nombre, por_defecto=False):
    """Convierte una variable de entorno en booleano ('1', 'true', 'si', 'yes')."""
    valor = os.getenv(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


def _env_lista(nombre, por_defecto=""):
    """Convierte una variable de entorno separada por comas en una lista."""
    return [v.strip() for v in os.getenv(nombre, por_defecto).split(",") if v.strip()]


# --- Seguridad --------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Falta SECRET_KEY. Copie .env.example a .env y complete sus valores."
    )

DEBUG = _env_bool("DEBUG", por_defecto=False)

ALLOWED_HOSTS = _env_lista("ALLOWED_HOSTS", "localhost,127.0.0.1")


# --- Aplicaciones -----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps del proyecto
    "detector",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "emosense.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Plantillas globales (base.html, inicio.html, ...)
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "emosense.wsgi.application"


# --- Base de datos (PostgreSQL) ---------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "emosense"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


# --- Validación de contraseñas (solo para el admin) -------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Internacionalización ---------------------------------------------------

LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True


# --- Archivos estáticos -----------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Límites de carga -------------------------------------------------------
# Los fotogramas JPEG se procesan solo en memoria; nunca se guardan en disco.

# Tamaño máximo del cuerpo de una petición (3 MB).
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
# Archivos subidos por debajo de este tamaño se mantienen en memoria (3 MB),
# evitando que Django los escriba en un archivo temporal.
FILE_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
# Solo el manejador en memoria: los archivos subidos nunca se escriben en disco.
# (Las peticiones mayores a 3 MB se rechazan antes de leer el archivo.)
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]
# Tamaño máximo aceptado para un fotograma/imagen (2 MB).
TAMANO_MAX_IMAGEN = 2 * 1024 * 1024


# --- Modelos de visión artificial -------------------------------------------

CARPETA_MODELOS = BASE_DIR / "modelos_ia"
