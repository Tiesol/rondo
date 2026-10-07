"""Settings para pytest: valores locales por defecto, sin depender de un .env."""

import os

os.environ.setdefault("SECRET_KEY", "solo-para-tests")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "postgres://rondo:rondo@localhost:5432/rondo")

from rondo.settings import *  # noqa: F403

# En los tests no hay collectstatic: sin manifiesto de archivos estáticos.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
