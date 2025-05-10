#!/bin/bash

mkdir -p /var/run/openvswitch
mkdir -p /etc/openvswitch

if [ ! -f /etc/openvswitch/conf.db ]; then
    ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
fi

ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --pidfile --detach

ovs-vswitchd --pidfile --detach || true

if command -v ryu-manager &> /dev/null; then
    ryu-manager &
else
    ovs-testcontroller ptcp:6653 &
fi

sleep 2

python3 manage.py migrate

python3 manage.py collectstatic --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    python3 manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD') if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists() else None"
fi

python3 -m uvicorn django_app.asgi:application --host 0.0.0.0 --port 8000 --reload