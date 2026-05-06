#!/usr/bin/env bash
set -e

echo "=== Render Build Script ==="
echo "Starting build at $(date)"

# Install Python dependencies (ignore mysqlclient on systems without MySQL dev libs)
echo "=== Installing Python dependencies ==="
pip install -r requirements.txt --no-cache-dir 2>/dev/null || {
    echo "Some packages failed, installing individually..."
    # Filter out mysqlclient which needs system libs
    grep -v mysqlclient requirements.txt > /tmp/requirements-nomysql.txt
    pip install -r /tmp/requirements-nomysql.txt --no-cache-dir
}
pip install gunicorn[gevent] whitenoise --no-cache-dir

# Try to build frontend if Node.js is available
echo "=== Checking frontend assets ==="
if command -v node &> /dev/null; then
    echo "Node.js found, building frontend..."
    cd frontend
    npm ci --omit=optional 2>/dev/null || npm install --omit=optional
    npm run build
    cd ..
else
    echo "Node.js not found, using pre-built frontend assets."
    echo "If you need to rebuild frontend, install Node.js 20+ locally and run: cd frontend && npm install && npm run build"
fi

# Verify frontend assets exist
if [ -f "blog/static/blog/dist/.vite/manifest.json" ]; then
    echo "Frontend assets verified: $(cat blog/static/blog/dist/.vite/manifest.json | python -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} entries')" 2>/dev/null || echo 'present')"
else
    echo "WARNING: No Vite manifest found! Run frontend build first."
fi

# Collect static files
echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --clear 2>/dev/null || echo "Static file collection deferred to runtime"

echo "=== Build complete ==="
