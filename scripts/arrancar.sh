#!/bin/sh
# Arranque del contenedor: migraciones y servidor. Hay una sola instancia, así que no
# hay riesgo de que dos migraciones corran a la vez.
set -e

python manage.py migrate --noinput

# El log de accesos registra la ruta sin la query string: ahí podría ir algún dato personal.
exec gunicorn rondo.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 1 --threads 4 \
    --timeout 300 \
    --access-logfile - \
    --access-logformat '%(h)s "%(m)s %(U)s" %(s)s %(L)ss'
