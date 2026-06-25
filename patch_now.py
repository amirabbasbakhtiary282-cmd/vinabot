#!/usr/bin/env python3
import os
import glob

recipes_dir = "/home/amirabbas/Vina/.buildozer/android/platform/python-for-android/pythonforandroid/recipes"

# Check if the directory exists
if not os.path.isdir(recipes_dir):
    print(f"Recipes dir not found: {recipes_dir}")
    exit(1)

# Patch openssl
openssl_file = os.path.join(recipes_dir, "openssl/__init__.py")
if os.path.exists(openssl_file):
    with open(openssl_file) as fh:
        content = fh.read()
    old_url = "https://www.openssl.org/source/openssl-{version}.tar.gz"
    new_url = "https://github.com/openssl/openssl/archive/refs/tags/openssl-{version}.tar.gz"
    if old_url in content:
        content = content.replace(old_url, new_url)
        with open(openssl_file, "w") as fh:
            fh.write(content)
        print(f"Patched: {openssl_file}")
    else:
        print(f"Already patched or URL not found: {openssl_file}")
else:
    print(f"Not found: {openssl_file}")

# Patch libwebp
libwebp_file = os.path.join(recipes_dir, "libwebp/__init__.py")
if os.path.exists(libwebp_file):
    with open(libwebp_file) as fh:
        content = fh.read()
    old_url = "https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-{version}.tar.gz"
    new_url = "https://github.com/webmproject/libwebp/archive/refs/tags/v{version}.tar.gz"
    if old_url in content:
        content = content.replace(old_url, new_url)
        with open(libwebp_file, "w") as fh:
            fh.write(content)
        print(f"Patched: {libwebp_file}")
    else:
        print(f"Already patched or URL not found: {libwebp_file}")
else:
    print(f"Not found: {libwebp_file}")

# Check for any other storage.googleapis.com URLs
print("\n--- Scanning for problematic URLs ---")
for recipe_init in glob.glob(os.path.join(recipes_dir, "*", "__init__.py")):
    with open(recipe_init, "r") as fh:
        content = fh.read()
    for domain in ["storage.googleapis.com", "www.openssl.org"]:
        if domain in content:
            recipe_name = os.path.basename(os.path.dirname(recipe_init))
            # Find the actual URL line
            for line in content.split("\n"):
                if "url" in line.lower() and domain in line:
                    print(f"  WARNING: {recipe_name}: {line.strip()}")
