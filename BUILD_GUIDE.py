# -*- coding: utf-8 -*-
"""
راهنمای ساخت APK وینا روی ویندوز 11 با WSL2
"""

BUILD_GUIDE = """
╔══════════════════════════════════════════════════════════════╗
║     راهنمای ساخت APK وینا روی ویندوز 11 با WSL2           ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۱: نصب WSL2 روی ویندوز ۱۱
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

۱. PowerShell را به عنوان Administrator باز کنید
۲. دستور زیر را اجرا کنید:

   wsl --install

۳. ری‌استارت کنید
۴. پس از ری‌استارت، Ubuntu باز می‌شود
۵. نام کاربری و رمز عبور انتخاب کنید

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۲: نصب ابزارهای لازم در WSL2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

در ترمینال Ubuntu:

   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3 python3-pip python3-venv
   sudo apt install -y git curl wget unzip zip
   sudo apt install -y openjdk-17-jdk
   sudo apt install -y autoconf libtool pkg-config
   sudo apt install -y zlib1g-dev libncurses5-dev libgdbm-dev
   sudo apt install -y libnss3-dev libssl-dev libreadline-dev
   sudo apt install -y libffi-dev libsqlite3-dev libbz2-dev

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۳: نصب Python-for-Android و Buildozer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   pip3 install --upgrade pip setuptools wheel
   pip3 install buildozer cython kivy

   # نصب SDK و NDK
   buildozer init

   # این دستور SDK و NDK را دانلود می‌کند (حدود ۳ GB)
   # منتظر بمانید تا تمام شود

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۴: کپی پروژه به WSL2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

پوشه پروژه وینا را از ویندوز به WSL2 کپی کنید:

   # در PowerShell ویندوز:
   wsl -- cp -r "D:\\Vina" /home/$USER/Vina

   # یا در WSL2:
   cp -r /mnt/d/Vina ~/Vina

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۵: نصب کتابخانه‌های Python
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   cd ~/Vina
   pip3 install -r requirements.txt

   # یا دستی:
   pip3 install kivy==2.1.0
   pip3 install llama-cpp-python
   pip3 install vosk
   pip3 install pyttsx3
   pip3 install SpeechRecognition
   pip3 install requests beautifulsoup4
   pip3 install numpy
   pip3 install cryptography

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۶: دانلود مدل‌ها
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   cd ~/Vina
   python3 src/model_downloader.py

   # یا دستی:
   mkdir -p models

   # دانلود Gemma-2-9B (حدود ۴.۵ GB)
   wget -O models/gemma-2-9b-q4_k_m.gguf \\
     "https://huggingface.co/google/gemma-2-9b-it-GGUF/resolve/main/gemma-2-9b-it-Q4_K_M.gguf"

   # دانلود Vosk فارسی (حدود ۵۰ MB)
   wget -O models/vosk-model-small-fa.zip \\
     "https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip"
   cd models && unzip vosk-model-small-fa.zip && cd ..

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۷: ساخت APK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   cd ~/Vina

   # ساخت APK debug
   buildozer -v android debug

   # این مرحله ۳۰ تا ۱۲۰ دقیقه طول می‌کشد!
   # اولین بار کتابخانه‌ها کامپایل می‌شوند

   # APK در پوشه bin قرار می‌گیرد:
   # bin/vinabot-1.0.0-debug.apk

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مرحله ۸: نصب APK روی گوشی
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   # با ADB:
   adb install bin/vinabot-1.0.0-debug.apk

   # یا فایل APK را به گوشی کپی کنید و نصب کنید

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  روش جایگزین: ساخت با Docker
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   docker pull kivy/buildozer
   docker run -it --rm -v $(pwd):home/user/hostcwd kivy/buildozer android debug

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  روش جایگزین: ساخت با Google Colab
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

یک نوت‌بوک Colab بسازید و دستورات زیر را اجرا کنید:

   !sudo apt-get update
   !sudo apt-get install -y git python3 openjdk-17-jdk
   !pip install buildozer cython kivy
   !git clone https://github.com/your-repo/vina.git
   !cd vina && buildozer android debug

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  مشکل‌یابی
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

مشکل: "SDK not found"
راه‌حل: buildozer sdkmanager را نصب کنید
   buildozer android sdkmanager

مشکل: "NDK not found"
راه‌حل:
   buildozer android ndk

مشکل: "Memory error"
راه‌حل: حافظه swap اضافه کنید
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile

مشکل: "Compilation error"
راه‌حل: نسخه‌ها را بروزرسانی کنید
   pip3 install --upgrade buildozer cython

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  نکات مهم
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• اولین ساخت حدود ۲ ساعت طول می‌کشد
• حداقل ۱۰ GB فضای خالی لازم است
• حداقل ۸ GB RAM برای کامپایل لازم است
• اتصال اینترنت پایدار لازم است
• APK نهایی حدود ۵۰-۱۰۰ MB خواهد بود (بدون مدل)
• مدل‌ها باید جداگانه دانلود و در گوشی قرار داده شوند

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  جایگزین: ساخت با Termux
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

اگر به کامپایلر دسترسی ندارید:

1. Termux را از F-Droid نصب کنید
2. دستورات زیر را اجرا کنید:

   pkg update && pkg upgrade
   pkg install python buildozer git
   pip install kivy buildozer
   buildozer android debug

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


if __name__ == '__main__':
    print(BUILD_GUIDE)
