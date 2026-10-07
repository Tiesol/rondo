"""Settings para pytest: valores locales por defecto, sin depender de un .env."""

import os

os.environ.setdefault("SECRET_KEY", "solo-para-tests")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "postgres://rondo:rondo@localhost:5432/rondo")

from rondo.settings import *  # noqa: F403
