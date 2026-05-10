#!/bin/bash
# =============================================================
# PythonAnywhere Deployment Script for DjangoBlog (lll2.top)
# =============================================================
# Usage: Run this script in a PythonAnywhere Bash console
#   bash deploy_pa.sh
#
# Prerequisites:
#   1. Create a PythonAnywhere account (free Hacker plan)
#   2. Open a Bash console on PythonAnywhere
# =============================================================

set -e

PA_USERNAME="${USER}"
PROJECT_DIR="/home/${PA_USERNAME}/DjangoBlog-master"
VENV_DIR="/home/${PA_USERNAME}/.virtualenvs/djangoblog"
PYTHON_VERSION="3.11"

echo "============================================"
echo "  DjangoBlog Deployment for PythonAnywhere"
echo "  User: ${PA_USERNAME}"
echo "  Project: ${PROJECT_DIR}"
echo "============================================"

# --- Step 1: Clone or update the repo ---
echo ""
echo "=== Step 1: Clone/update repository ==="
if [ -d "${PROJECT_DIR}/.git" ]; then
    echo "Repository exists, pulling latest changes..."
    cd "${PROJECT_DIR}"
    git pull origin main
else
    echo "Cloning repository..."
    cd /home/${PA_USERNAME}
    git clone https://github.com/LZL-LLL/DjangoBlog.git DjangoBlog-master
    cd "${PROJECT_DIR}"
fi

# --- Step 2: Create virtualenv ---
echo ""
echo "=== Step 2: Create Python virtualenv ==="
if [ ! -d "${VENV_DIR}" ]; then
    mkvirtualenv --python=/usr/bin/python${PYTHON_VERSION} djangoblog
else
    echo "Virtualenv already exists at ${VENV_DIR}"
fi

# Activate virtualenv
source "${VENV_DIR}/bin/activate" 2>/dev/null || workon djangoblog

# --- Step 3: Install dependencies ---
echo ""
echo "=== Step 3: Install Python dependencies ==="
cd "${PROJECT_DIR}"
pip install -r requirements-pa.txt --no-cache-dir

# --- Step 4: Build frontend assets (pre-built in repo) ---
echo ""
echo "=== Step 4: Check frontend assets ==="
if [ -f "blog/static/blog/dist/.vite/manifest.json" ]; then
    echo "Frontend assets found (pre-built in repo)."
else
    echo "WARNING: No Vite manifest found. Frontend assets may need building."
    echo "If you have Node.js available, run: cd frontend && npm install && npm run build"
fi

# --- Step 5: Django setup ---
echo ""
echo "=== Step 5: Django setup ==="

# Set environment for setup
export DJANGO_SETTINGS_MODULE=djangoblog.settings
export DJANGO_DEBUG=False
export COMPRESS_ENABLED=False
export ALLOWED_HOSTS="lll2.top,www.lll2.top,.pythonanywhere.com,localhost"
export CSRF_TRUSTED_ORIGINS="https://lll2.top,https://www.lll2.top,https://*.pythonanywhere.com"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Building search index..."
python manage.py rebuild_index --noinput 2>/dev/null || echo "Search index build skipped (may need data first)"

echo "Compiling translations..."
python manage.py compilemessages 2>/dev/null || echo "Translation compilation skipped"

# --- Step 6: Verify ---
echo ""
echo "=== Step 6: Verification ==="
python manage.py check --deploy 2>&1 || true

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "Next steps (do these in the PythonAnywhere Web tab):"
echo ""
echo "1. Go to Web tab -> Add a new web app"
echo "2. Choose 'Manual configuration' -> Python ${PYTHON_VERSION}"
echo "3. Set Source code: ${PROJECT_DIR}"
echo ""
echo "4. Edit WSGI configuration file:"
echo "   Replace contents with:"
echo "   ---------------------------------------------------"
echo "   import os, sys"
echo "   path = '${PROJECT_DIR}'"
echo "   if path not in sys.path:"
echo "       sys.path.append(path)"
echo "   os.environ['DJANGO_SETTINGS_MODULE'] = 'djangoblog.settings'"
echo "   from djangoblog.wsgi import application"
echo "   ---------------------------------------------------"
echo ""
echo "5. Set Virtualenv path: ${VENV_DIR}"
echo ""
echo "6. Static files mapping (add two entries):"
echo "   URL: /static/  -> Directory: ${PROJECT_DIR}/collectedstatic"
echo "   URL: /media/   -> Directory: ${PROJECT_DIR}/uploads"
echo ""
echo "7. Click 'Reload' to start the app"
echo ""
echo "8. Cloudflare DNS:"
echo "   Add CNAME: lll2.top -> ${PA_USERNAME}.pythonanywhere.com (proxied)"
echo "   Add CNAME: www -> ${PA_USERNAME}.pythonanywhere.com (proxied)"
echo ""
echo "9. Cloudflare SSL/TLS: Set to 'Full'"
echo "   Enable 'Always Use HTTPS'"
echo ""
