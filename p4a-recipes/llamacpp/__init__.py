# -*- coding: utf-8 -*-
"""
Custom python-for-android recipe: builds libllama.so + libggml*.so for
Android from the official llama.cpp source (CMake + NDK toolchain).

چرا این recipe سفارشی است؟
llama-cpp-python در buildozer.spec اصلی پروژه به همین دلیل حذف شده بود
که کراس‌کامپایل آن برای اندروید غیرقابل‌اعتماد است. اما llama.cpp خودِ
سازنده رسمی از CMake + Android NDK toolchain پشتیبانی می‌کند (این روش
توسط تیم llama.cpp مستند و آزمایش شده است)، پس یک recipe اختصاصی که
مستقیماً از CMake استفاده می‌کند - نه از pip/setuptools - راه‌حل پایدار
است.

خروجی این recipe: libggml-base.so, libggml-cpu.so, libggml.so, libllama.so
"""
from multiprocessing import cpu_count
from os.path import join

import sh

from pythonforandroid.logger import shprint, info
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory


class LlamaCppRecipe(Recipe):
    # نسخه‌ی پین‌شده و تست‌شده (به‌جای master، برای بازتولیدپذیری بیلد)
    version = "b5026"
    url = "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/refs/tags/{version}"
    # نام پوشه‌ی استخراج‌شده از تاربال codeload با نام معمول release متفاوت است
    # (llama.cpp-b5026) بنابراین به‌صورت صریح مشخص می‌کنیم.

    depends = []
    built_libraries = {
        "libggml-base.so": "build/bin",
        "libggml-cpu.so": "build/bin",
        "libggml.so": "build/bin",
        "libllama.so": "build/bin",
    }

    def get_build_dir(self, arch):
        # codeload tarball برای تگ b5026 پوشه‌ی llama.cpp-b5026 می‌سازد
        return join(self.get_build_container_dir(arch), "llama.cpp-" + self.version)

    # نکته: متد should_build را عمداً override نمی‌کنیم. کلاس پایه‌ی Recipe
    # وقتی built_libraries تعریف شده باشد، به‌صورت پیش‌فرض بررسی می‌کند که
    # آیا فایل‌های .so قبلاً ساخته شده‌اند یا نه (از طریق get_libraries)، و
    # پس از build_arch نیز به‌صورت خودکار install_libraries را برای کپی
    # کردن آن‌ها به مسیر نهایی فراخوانی می‌کند. بازنویسی این متد با API
    # نادرست (ctx.has_libs که اصلاً وجود ندارد) باعث خطا در بیلد می‌شد.

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        build_dir = self.get_build_dir(arch.arch)

        toolchain_file = join(self.ctx.ndk_dir, "build", "cmake", "android.toolchain.cmake")

        info(f"Building llama.cpp for arch={arch.arch} api={self.ctx.ndk_api}")

        with current_directory(build_dir):
            shprint(
                sh.cmake,
                "-B", "build",
                "-DCMAKE_TOOLCHAIN_FILE=" + toolchain_file,
                "-DANDROID_ABI=" + arch.arch,
                "-DANDROID_PLATFORM=android-" + str(self.ctx.ndk_api),
                "-DANDROID_STL=c++_shared",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DBUILD_SHARED_LIBS=ON",
                # موارد زیر برای اپلیکیشن موبایل غیرضروری‌اند و زمان/حجم بیلد را کم می‌کنند
                "-DLLAMA_BUILD_TESTS=OFF",
                "-DLLAMA_BUILD_EXAMPLES=OFF",
                "-DLLAMA_BUILD_SERVER=OFF",
                "-DLLAMA_CURL=OFF",
                "-DGGML_LLAMAFILE=OFF",
                "-DGGML_OPENMP=OFF",
                # اندروید معماری‌های متفاوتی دارد؛ از تشخیص خودکار CPU میزبان صرف‌نظر کن
                "-DGGML_NATIVE=OFF",
                _env=env,
            )
            shprint(sh.cmake, "--build", "build", "--config", "Release",
                    "-j", str(cpu_count()), _env=env)

    def get_recipe_env(self, arch=None):
        env = super().get_recipe_env(arch)
        return env


recipe = LlamaCppRecipe()
