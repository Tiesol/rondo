"""Settings de Rondo. Todo lo que cambia entre entornos sale de variables de entorno."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

RAIZ = Path(__file__).resolve().parents[2]
BASE_DIR = RAIZ  # lo usa django-tailwind-cli


def _lista(nombre: str) -> list[str]:
    return [valor.strip() for valor in os.environ.get(nombre, "").split(",") if valor.strip()]


DEBUG = os.environ.get("DEBUG", "false").lower() in {"1", "true", "si", "yes"}

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Falta la variable de entorno SECRET_KEY.")

ALLOWED_HOSTS = _lista("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = _lista("CSRF_TRUSTED_ORIGINS")

# Render define la dirección pública del servicio en esta variable (demo en Render).
if render_host := os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(render_host)
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_host}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "django_tailwind_cli",
    "torneo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Toda vista pide login salvo que se marque con @login_not_required (SPEC, "Límites").
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "rondo.urls"
WSGI_APPLICATION = "rondo.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ImproperlyConfigured("Falta la variable de entorno DATABASE_URL.")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=60,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [RAIZ / "assets"]
STATIC_ROOT = RAIZ / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# El usuario se escribe sin importar mayúsculas: el teclado del celular pone la primera sola.
AUTHENTICATION_BACKENDS = ["torneo.autenticacion.UsuarioSinMayusculasBackend"]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "login"

# Tailwind se compila con su ejecutable propio (sin Node). La salida va a assets/css/,
# que no entra al repo: se genera con `manage.py tailwind build`.
TAILWIND_CLI_SRC_CSS = "frontend/tailwind.css"
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"

# Logs a la salida estándar (Cloud Logging los toma de ahí). Nunca se registran cuerpos
# de requests ni formularios: pueden tener datos personales de menores.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": "INFO"},
}

if not DEBUG:
    # Cloud Run termina TLS y avisa el protocolo original en este encabezado.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # El dominio *.run.app es de Google: no se puede inscribir en la lista de precarga HSTS.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]
