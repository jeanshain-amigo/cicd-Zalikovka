#!/usr/bin/env bash
set -o errexit

echo "Applying migrations..."
python manage.py migrate
echo "Migrations applied successfully!"
