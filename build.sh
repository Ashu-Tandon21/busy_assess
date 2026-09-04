#!/usr/bin/env bash
# Render build command. Also works fine as a generic "install + prep" script
# for any host that gives you a shell before starting the process.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
