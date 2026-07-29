# -*- coding: utf-8 -*-
"""
Custom python-for-android recipe: compiles Vina's thin C-ABI bridge
(src/vina_llm.cpp, shipped alongside this recipe) against the llama.cpp
libraries built by the `llamacpp` recipe, producing libvina_llm.so for
the target Android ABI.

سورس اصلی (src/vina_llm.cpp) کنار همین recipe نگه‌داری می‌شود تا این
پکیج کاملاً خودکفا باشد و به مسیر پروژه‌ی اصلی وابسته نباشد.
"""
from os.path import join, dirname, abspath, exists

import sh

from pythonforandroid.logger import shprint, info
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory, ensure_dir


def arch_name(arch):
    """نام معماری را برمی‌گرداند، چه شیء Arch داده شود چه رشته.

    چرا این تابع لازم است؟ python-for-android در فراخوانی متدهای recipe
    یکدست نیست (تأییدشده از pythonforandroid/build.py):

        prepare_build_dir(arch)   -> **رشته**  (خط ۵۱۲: arch.arch پاس می‌شود)
        prebuild_arch(arch)       -> شیء Arch  (خط ۵۲۲)
        should_build(arch)        -> شیء Arch  (خط ۵۲۹)
        build_arch(arch)          -> شیء Arch  (خط ۵۳۰)
        install_libraries(arch)   -> شیء Arch  (خط ۵۳۳)

    نوشتن ``arch.arch`` داخل prepare_build_dir باعث این خطا می‌شد:
        AttributeError: 'str' object has no attribute 'arch'

    با این تابع، هر دو حالت درست کار می‌کند و دیگر لازم نیست به خاطر
    بسپاریم کدام متد چه چیزی می‌گیرد.
    """
    return arch if isinstance(arch, str) else arch.arch


class VinaLlmRecipe(Recipe):
    version = "1.0"
    url = None
    depends = ["llamacpp"]
    built_libraries = {"libvina_llm.so": "."}

    # نکته: should_build و install_libraries را override نمی‌کنیم؛ کلاس
    # پایه‌ی Recipe از روی built_libraries به‌درستی تشخیص می‌دهد که آیا
    # نیاز به بازسازی هست و پس از build_arch به‌صورت خودکار .so ساخته‌شده
    # را به مسیر نهایی کپی می‌کند.

    @property
    def _src_file(self):
        return join(dirname(abspath(__file__)), "src", "vina_llm.cpp")

    def get_build_dir(self, arch):
        return join(self.get_build_container_dir(arch), "vinallm")

    def prepare_build_dir(self, arch):
        # توجه: اینجا p4a یک *رشته* پاس می‌دهد، نه شیء Arch.
        ensure_dir(self.get_build_dir(arch_name(arch)))

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        build_dir = self.get_build_dir(arch_name(arch))

        src_file = self._src_file
        if not exists(src_file):
            raise FileNotFoundError(f"سورس vina_llm.cpp پیدا نشد: {src_file}")

        info(f"Building vina_llm shim from: {src_file}")

        llamacpp_recipe = self.get_recipe("llamacpp", self.ctx)
        llama_build_dir = llamacpp_recipe.get_build_dir(arch_name(arch))
        llama_include = join(llama_build_dir, "include")
        ggml_include = join(llama_build_dir, "ggml", "include")
        llama_lib_dir = join(llama_build_dir, "build", "bin")

        clang = env.get("CC", "clang").split()[0]
        out_lib = join(build_dir, "libvina_llm.so")

        with current_directory(build_dir):
            shprint(
                sh.Command(clang),
                "-std=c++17", "-shared", "-fPIC", "-O2",
                "-I", llama_include,
                "-I", ggml_include,
                src_file,
                "-o", out_lib,
                "-L", llama_lib_dir,
                "-lllama", "-lggml", "-lggml-base", "-lggml-cpu",
                "-lc++_shared",
                _env=env,
            )

    def get_recipe_env(self, arch=None):
        env = super().get_recipe_env(arch)
        return env


recipe = VinaLlmRecipe()
