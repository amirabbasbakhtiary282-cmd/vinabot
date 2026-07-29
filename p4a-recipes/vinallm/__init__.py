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

    # libvina_llm.so و کتابخانه‌های llama.cpp با c++_shared لینک می‌شوند،
    # پس libc++_shared.so باید داخل APK قرار بگیرد وگرنه برنامه هنگام
    # بارگذاری کتابخانه با «library "libc++_shared.so" not found» کرش
    # می‌کند. این پرچم باعث می‌شود p4a خودش آن را از NDK کپی کند.
    need_stl_shared = True

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

        # ------------------------------------------------------------------
        # انتخاب کامپایلر - نکته‌ی حیاتی
        # ------------------------------------------------------------------
        # نسخه‌ی قبلی این‌طور کامپایلر را انتخاب می‌کرد:
        #
        #     clang = env.get("CC", "clang").split()[0]
        #
        # و این دقیقاً همان چیزی بود که بیلد را می‌شکست. python-for-android
        # متغیر CC را به این شکل می‌سازد (archs.py: Arch.get_env):
        #
        #     CC = "{ccache} {clang_exe} {cflags}"
        #
        # یعنی وقتی ccache روی سیستم نصب باشد (روی رانرهای GitHub Actions
        # همیشه هست)، مقدار CC چیزی شبیه این است:
        #
        #     /usr/bin/ccache /path/to/clang -target aarch64-... -fPIC ...
        #
        # پس split()[0] برابر «/usr/bin/ccache» می‌شد و ما ccache را
        # به‌عنوان کامپایلر صدا می‌زدیم. خطای واقعی در لاگ بیلد:
        #
        #     RAN: /usr/bin/ccache -std=c++17 -shared -fPIC ...
        #     STDOUT: /usr/bin/ccache: invalid option -- 't'
        #
        # (ccache گزینه‌ی «-std=...» را نمی‌شناسد و روی «-t» گیر می‌کند.)
        #
        # به‌جای بازی با رشته‌ی CC، مستقیماً از خود شیء Arch مسیر کامل
        # clang++ را می‌گیریم (arch.clang_exe_cxx) و پرچم‌های معماری را هم
        # صریح و جداگانه اضافه می‌کنیم. این کار هم از ccache مستقل است و
        # هم دیگر به قالب رشته‌ی CC وابسته نیست.
        #
        # ضمناً clang++ باید با C++ کامپایل کند (نه clang ساده)، چون
        # vina_llm.cpp از std::string/std::vector و لامبدا استفاده می‌کند.
        env = self.get_recipe_env(arch, with_flags_in_cc=False)
        compiler = arch.clang_exe_cxx

        # -target مشخص می‌کند برای کدام ABI و کدام سطح API کامپایل شود؛
        # از NDK r19 به بعد همین یک پرچم کافی است و sysroot به‌صورت خودکار
        # پیدا می‌شود (نیازی به standalone toolchain نیست).
        arch_flags = ["-target", arch.target] + list(arch.arch_cflags)

        out_lib = join(build_dir, "libvina_llm.so")

        with current_directory(build_dir):
            shprint(
                sh.Command(compiler),
                *arch_flags,
                "-std=c++17", "-shared", "-fPIC", "-O2",
                "-fvisibility=hidden",
                "-I", llama_include,
                "-I", ggml_include,
                src_file,
                "-o", out_lib,
                "-L", llama_lib_dir,
                "-lllama", "-lggml", "-lggml-base", "-lggml-cpu",
                # وقتی APK اجرا می‌شود، همه‌ی .soها کنار هم در پوشه‌ی lib
                # برنامه قرار دارند، پس نیازی به rpath نیست؛ اما لینکر باید
                # مطمئن شود هیچ سمبل حل‌نشده‌ای باقی نمانده تا خطاهای
                # بارگذاری به زمان اجرا موکول نشوند.
                "-Wl,--no-undefined",
                "-lc++_shared", "-llog", "-lm",
                _env=env,
            )

        if not exists(out_lib):
            raise RuntimeError(
                "کامپایل libvina_llm.so بدون خطا تمام شد ولی فایل خروجی "
                f"ساخته نشد: {out_lib}"
            )
        info(f"vina_llm: built {out_lib}")


recipe = VinaLlmRecipe()
