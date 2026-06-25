#!/usr/bin/env python3
import os
import glob

home = os.path.expanduser("~")

search_paths = [
    os.path.join(home, "Vina", "Vina", ".buildozer", "android", "platform", "python-for-android"),
    os.path.join(home, ".buildozer", "android", "platform", "python-for-android"),
]

patches = {
    "openssl": {
        "old": "https://www.openssl.org/source/openssl-{version}.tar.gz",
        "new": "https://github.com/openssl/openssl/archive/refs/tags/openssl-{version}.tar.gz",
    },
    "libwebp": {
        "old": "https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-{version}.tar.gz",
        "new": "https://github.com/webmproject/libwebp/archive/refs/tags/v{version}.tar.gz",
    },
    "freetype": {
        "old": "https://download.savannah.gnu.org/releases/freetype/freetype-{version}.tar.gz",
        "new": "https://github.com/freetype/freetype/archive/refs/tags/VER-{version}.tar.gz",
    },
}

patched = []

for search_path in search_paths:
    recipes_dir = os.path.join(search_path, "pythonforandroid", "recipes")
    if not os.path.exists(recipes_dir):
        continue

    print(f"Found recipes at: {recipes_dir}")

    for recipe_name, patch_info in patches.items():
        init_file = os.path.join(recipes_dir, recipe_name, "__init__.py")
        if not os.path.exists(init_file):
            print(f"  SKIP: {recipe_name} not found at {init_file}")
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

if not patched:
    print("\nNo recipes found. python-for-android might not be cloned yet.")
    print("Run 'buildozer android debug' once first to clone it.")
else:
    print(f"\nDone. Patched: {patched}")
