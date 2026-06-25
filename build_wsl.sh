#!/bin/bash
set -e

echo "=== وینا Vina AI - ساختن APK ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/7] فعال‌سازی محیط مجازی..."
if [ -d "/home/amirabbas/venv" ]; then
    source /home/amirabbas/venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "ERROR: virtual env not found at /home/amirabbas/venv or ./venv"
    exit 1
fi

echo "[2/7] نصب وابستگی‌های Buildozer..."
pip install --upgrade buildozer cython 2>&1

echo "[3/7] پچ کردن OpenSSL recipe..."
python3 fix_openssl.py

echo "[4/7] پچ کردن python-for-android recipes..."
python3 patch_recipes.py

echo "[5/7] پچ کردن android wrapper..."
python3 fix_android_wrapper.py

echo "[6/7] پاک کردن کش Buildozer..."
rm -rf .buildozer

echo "[7/7] اجرای Buildozer..."
export BUILDOZER_ALLOW_UNSAFE_DISTRIBUTION=1
buildozer -v android debug 2>&1

echo ""
echo "=== پایان ==="
echo "خروجی APK در bin/ قرار دارد."
exit 0
