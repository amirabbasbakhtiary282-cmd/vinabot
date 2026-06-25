#!/usr/bin/env python3
"""دانلود خودکار مدل‌های مورد نیاز وینا"""
import os
import sys
import zipfile
import urllib.request
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip"


def download_file(url, dest):
    print(f"دانلود {url.split('/')[-1]}...")
    try:
        import requests
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 / total
                        print(f"\r{pct:.0f}%", end="", flush=True)
        print()
        return True
    except ImportError:
        print("  (requests not available, using urllib)")
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"خطا: {e}")
        return False


def extract_zip(zip_path, extract_to):
    print(f"استخراج {os.path.basename(zip_path)}...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_to)
    extracted_dir = os.path.join(extract_to, "vosk-model-small-fa-0.5")
    target_dir = os.path.join(extract_to, "vosk-model-small-fa")
    if os.path.exists(extracted_dir) and not os.path.exists(target_dir):
        os.rename(extracted_dir, target_dir)
        print(f"  -> {target_dir}")
    os.remove(zip_path)
    print("انجام شد.")


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    vosk_target = os.path.join(MODELS_DIR, "vosk-model-small-fa")
    if os.path.exists(vosk_target):
        print(f"✓ مدل Vosk از قبل وجود دارد: {vosk_target}")
    else:
        print("✗ مدل Vosk پیدا نشد. در حال دانلود...")
        zip_dest = os.path.join(MODELS_DIR, "vosk-model-small-fa.zip")
        if download_file(VOSK_URL, zip_dest):
            extract_zip(zip_dest, MODELS_DIR)
        else:
            print("خطا در دانلود مدل Vosk")

    print("\n--- وضعیت نهایی ---")
    for item in os.listdir(MODELS_DIR):
        path = os.path.join(MODELS_DIR, item)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        if os.path.isdir(path):
            import glob
            files = glob.glob(os.path.join(path, "**", "*"), recursive=True)
            size = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
            print(f"  {item}/  ({size / 1024 / 1024:.1f} MB)")
        else:
            print(f"  {item}  ({size / 1024 / 1024:.1f} MB)")

    print("\n✓ آماده ساخت APK!")


if __name__ == "__main__":
    main()
