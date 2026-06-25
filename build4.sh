#!/bin/bash
set -e
source /home/amirabbas/venv/bin/activate
cd /home/amirabbas/Vina

# Don't clean - reuse downloaded packages
echo "=== Starting build ==="
/home/amirabbas/venv/bin/buildozer -v android debug 2>&1
echo "Build finished with exit code: $?"
