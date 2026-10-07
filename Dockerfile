# Imagen única de Rondo: sirve para Render (demo) y para Cloud Run (después).
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencias primero, para aprovechar la caché de capas.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# CSS de Tailwind y archivos estáticos. Las variables son ficticias: solo sirven para
# cargar los settings durante el build. Los valores reales llegan al arrancar.
RUN export SECRET_KEY=solo-build DATABASE_URL=postgres://build@localhost/build \
    && python manage.py tailwind build \
    && python manage.py collectstatic --noinput \
    && rm -rf .django_tailwind_cli

RUN useradd --system --create-home rondo
USER rondo

CMD ["scripts/arrancar.sh"]
