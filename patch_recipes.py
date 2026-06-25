#!/usr/bin/env python3
"""Patch all p4a recipes with broken download URLs."""
import os
import glob

recipes_dir = os.path.expanduser(
    "~/.buildozer/android/platform/python-for-android/pythonforandroid/recipes"
)

patches = {
    "openssl": {
        "old": "https://www.openssl.org/source/openssl-{version}.tar.gz",
        "new": "https://github.com/openssl/openssl/archive/refs/tags/openssl-{version}.tar.gz",
    },
    "libwebp": {
        "old": "https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-{version}.tar.gz",
        "new": "https://github.com/webmproject/libwebp/archive/refs/tags/v{version}.tar.gz",
    },
}

patched = []
for recipe_name, patch_info in patches.items():
    init_file = os.path.join(recipes_dir, recipe_name, "__init__.py")
    if not os.path.exists(init_file):
        print(f"  SKIP: {recipe_name} recipe not found at {init_file}")
        continue
    with open(init_file, "r") as f:
        content = f.read()
    if patch_info["old"] in content:
        content = content.replace(patch_info["old"], patch_info["new"])
        with open(init_file, "w") as f:
            f.write(content)
        patched.append(recipe_name)
        print(f"  PATCHED: {recipe_name}")
    else:
        print(f"  SKIP: {recipe_name} URL already patched or not found")

# Now scan for any other URLs that might 403
print("\n--- Scanning all recipes for potentially broken URLs ---")
for recipe_init in glob.glob(os.path.join(recipes_dir, "*", "__init__.py")):
    with open(recipe_init, "r") as f:
        content = f.read()
    # Check for common problematic domains
    for domain in ["storage.googleapis.com", "www.openssl.org"]:
        if domain in content:
            recipe_name = os.path.basename(os.path.dirname(recipe_init))
            if recipe_name not in patched:
                print(f"  WARNING: {recipe_name} uses {domain}")

print(f"\nDone. Patched: {patched}")
