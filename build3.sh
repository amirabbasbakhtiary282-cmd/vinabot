#!/bin/bash
set -e
source /home/amirabbas/venv/bin/activate
cd /home/amirabbas/Vina

# Only clean the build output, not the downloaded packages
rm -rf .buildozer/android/platform/build-arm64-v8a
rm -f .buildozer/android/platform/.sdk_fix

# If p4a isn't cloned yet, buildozer will clone it
if [ ! -d ".buildozer/android/platform/python-for-android" ]; then
    echo "=== Cloning python-for-android ==="
    git clone -b develop --single-branch https://github.com/kivy/python-for-android.git .buildozer/android/platform/python-for-android
fi

echo "=== Patching recipes ==="
python3 /mnt/d/Vina/patch_recipes.py

echo "=== Starting build ==="
/home/amirabbas/venv/bin/buildozer -v android debug 2>&1
echo "Build finished with exit code: $?"
