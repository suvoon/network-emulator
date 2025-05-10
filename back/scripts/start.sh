#!/bin/bash

service openvswitch-switch start

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 1
  echo "Still waiting for PostgreSQL..."
done
echo "PostgreSQL started"

sleep 5

mkdir -p /app/staticfiles

echo "Creating new migrations..."
python3 manage.py makemigrations django_app --noinput

echo "Applying migrations..."
python3 manage.py migrate --noinput

python3 manage.py collectstatic --noinput --clear

if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python3 manage.py createsuperuser \
        --noinput \
        --username $DJANGO_SUPERUSER_USERNAME \
        --email $DJANGO_SUPERUSER_EMAIL
fi

exec uvicorn django_app.asgi:application --host 0.0.0.0 --port 8000 --reload 