#!/bin/sh
set -e

if [ "$1" = 'manage.py' ]; then
  echo "Starting server..."
  ./manage.py migrate
  ./manage.py collectstatic --noinput
  exec /usr/local/bin/gunicorn xxxpheno.wsgi:application -w 2 -b :8000
fi
echo "Running command..."
exec "$@"
