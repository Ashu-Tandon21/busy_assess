#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py migrate
python manage.py collectstatic --noinput

if [ "${SEED_DEMO:-false}" = "true" ]; then
    python manage.py seed_demo
fi
