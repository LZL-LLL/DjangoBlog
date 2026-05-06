#!/usr/bin/env bash
set -e

echo "=== Render Start Script ==="
echo "Starting at $(date)"

# Run database migrations
echo "=== Running migrations ==="
python manage.py migrate --noinput

# Build search index (silently fail if not ready)
echo "=== Building search index ==="
python manage.py build_index --noinput 2>/dev/null || echo "Search index build deferred"

# Start gunicorn
echo "=== Starting Gunicorn ==="
exec gunicorn djangoblog.wsgi:application \
    --workers 2 \
    --worker-class gevent \
    --bind 0.0.0.0:${PORT:-8000} \
    --log-level info \
    --access-logfile - \
    --timeout 120 \
    --worker-connections 1000
