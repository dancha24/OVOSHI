#!/bin/sh
set -e
# makemigrations при каждом старте опасен в проде (случайные миграции, рассинхрон с репо).
# Только если явно: DJANGO_AUTOMAKEMIGRATIONS=1
if [ "${DJANGO_AUTOMAKEMIGRATIONS:-}" = "1" ]; then
  echo "DJANGO_AUTOMAKEMIGRATIONS=1 — makemigrations..."
  python manage.py makemigrations --noinput
fi
echo "Applying migrations..."
python manage.py migrate --noinput
echo "Ensure superuser (if OVOSHI_ADMIN_* set and no superuser yet)..."
python manage.py ensure_superuser
echo "Sync SocialApp (VK) from env if VK_CLIENT_ID set..."
python manage.py ensure_socialapps
echo "Collect static (admin CSS/JS для gunicorn + WhiteNoise)..."
python manage.py collectstatic --noinput
echo "Starting server..."
exec "$@"
