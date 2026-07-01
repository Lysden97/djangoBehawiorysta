#!/usr/bin/env bash

set -euo pipefail

python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec python -m gunicorn \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --access-logfile - \
  --error-logfile - \
  djangoBehawiorysta.wsgi:application
