#!/usr/bin/env bash


python manage.py collectstatic --noinput --clear
python manage.py migrate --noinput
python -m gunicorn --bind 0.0.0.0:8000 --workers 3 djangoBehawiorysta.wsgi:application
