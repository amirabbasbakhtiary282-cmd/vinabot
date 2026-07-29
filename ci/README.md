# CI — چرا این فایل اینجاست و چطور اعمالش کنید

## خلاصه‌ی یک‌خطی

فایل `ci/build-apk.proposed.yml` نسخه‌ی درست workflow است.
**شما** باید آن را در `.github/workflows/build.yml` کپی کنید (سه دستور
پایین) چون توکن من اجازه‌ی نوشتن روی پوشه‌ی workflows را ندارد.

```bash
cp ci/build-apk.proposed.yml .github/workflows/build.yml
git add .github/workflows/build.yml
git commit -m "CI: fail on real build errors, verify APK, run tests first"
git push origin arena/019fafa0-vinabot
```

بعد از این push، بیلد APK **خودکار** روی همین شاخه شروع می‌شود.

---

## چرا خودم این کار را نکردم؟

هر دو راه ممکن تست شد و هر دو با ۴۰۳ رد شدند:

```
$ git push
 ! [remote rejected] refusing to allow a GitHub App to create or update
   workflow `.github/workflows/build.yml` without `workflows` permission

$ gh workflow run build.yml
 HTTP 403: Resource not accessible by integration
```

یعنی نه می‌توانم فایل workflow را تغییر دهم، نه می‌توانم بیلد را دستی
اجرا کنم. workflow فعلی هم فقط روی `main`/`master` اجرا می‌شود، پس روی
این شاخه اصلاً اجرا نمی‌شود.

---

## مشکل اصلی که پیدا و رفع شد

### علائم

اجرای شماره ۷ (`30483807311`) در GitHub Actions **سبز** بود، اما:

- حجم artifact فقط **۲۷۶ کیلوبایت** بود
- محتوایش فقط `build.log` بود
- **هیچ APK ای وجود نداشت**

### علت واقعی شکست بیلد

از لاگ خام همان اجرا (نه حدس):

```
File "p4a-recipes/vinallm/__init__.py", line 83, in build_arch
RAN: /usr/bin/ccache -std=c++17 -shared -fPIC -O2 ...
STDOUT: /usr/bin/ccache: invalid option -- 't'
```

recipe کامپایلر را این‌طور انتخاب می‌کرد:

```python
clang = env.get("CC", "clang").split()[0]
```

اما python-for-android مقدار `CC` را این‌طور می‌سازد
(`pythonforandroid/archs.py`, `Arch.get_env`):

```python
env['CC'] = '{ccache}{exe} {cflags}'
```

روی رانرهای GitHub که ccache نصب است، `CC` می‌شود:

```
/usr/bin/ccache /path/to/clang -target aarch64-... -fPIC ...
```

پس `split()[0]` برابر `/usr/bin/ccache` بود و **ccache به‌عنوان کامپایلر**
صدا زده می‌شد. ccache گزینه‌ی `-std=c++17` را نمی‌شناسد و روی `-t` خطا داد.

> نکته: این باگ روی ماشینی که ccache نصب نباشد **ظاهر نمی‌شود**. برای
> همین تشخیصش سخت بود.

**رفع:** حالا مستقیماً از `arch.clang_exe_cxx` استفاده می‌شود (مسیر خالص
کامپایلر، بدون پرچم و بدون ccache) و پرچم‌های `-target` و `arch_cflags`
صریح پاس داده می‌شوند.

تست رگرسیون: `tests/test_recipe_compiler_selection.py`
(بررسی شد که با برگرداندن کد قدیمی واقعاً قرمز می‌شود.)

### چرا شکست پنهان ماند؟ (دو باگ مستقل)

**۱. `tee` کد خروجی را می‌بلعد**

```yaml
buildozer -v android debug 2>&1 | tee build.log
echo "BUILD_RESULT=$?" >> $GITHUB_ENV
```

در یک pipeline، کد خروجی متعلق به **آخرین** دستور (`tee`) است که همیشه
موفق است. اثبات عملی:

```bash
$ bash -c '(exit 1) | tee f; echo $?'
0                      # ← شکست پنهان شد
$ bash -c 'set -o pipefail; (exit 1) | tee f; echo $?'
1                      # ← درست
```

ضمناً آن خط `$?` هم کد خروجی `echo` قبلی را می‌خواند، نه buildozer، و
هیچ‌جا هم بررسی نمی‌شد.

**۲. نبود APK فقط «هشدار» بود**

```yaml
if-no-files-found: warn      # ← نبود APK = هشدار، نه خطا
if: always()                 # ← حتی بعد از شکست هم artifact می‌ساخت
```

نتیجه: artifact ای شامل فقط `build.log` تولید می‌شد و مرحله سبز می‌ماند.

---

## چه چیزی در workflow جدید عوض شد

| # | تغییر | چرا |
|---|-------|-----|
| ۱ | `set -o pipefail` | شکست buildozer دیگر پنهان نمی‌شود |
| ۲ | مرحله‌ی `Verify APK exists` | وجود واقعی فایل، حجم منطقی (>۵MB)، و حضور `libllama.so` / `libvina_llm.so` / `libc++_shared.so` داخل APK بررسی می‌شود |
| ۳ | `if-no-files-found: error` | نبود APK یعنی شکست |
| ۴ | حذف `if: always()` از آپلود APK | artifact «موفق» بدون APK غیرممکن شد |
| ۵ | جدا شدن `build.log` در artifact مستقل | لاگ همیشه هست، ولی artifact APK دیگر هرگز خالی نیست |
| ۶ | اجرا روی `arena/**` و PR | تست *قبل* از merge، نه بعدش |
| ۷ | مرحله‌ی تست قبل از بیلد | بیلد ۱-۳ ساعته نباید با یک خطای نگارشی هدر برود |
| ۸ | `Free up disk space` | بیلد p4a از ۲۰GB عبور می‌کند و پر شدن دیسک خطاهای گمراه‌کننده می‌دهد |
| ۹ | کش buildozer | بیلدهای بعدی بسیار سریع‌تر |
| ۱۰ | `concurrency` | بیلدهای موازی روی یک شاخه لغو می‌شوند |
| ۱۱ | چاپ SHA256 در Summary | تأیید یکپارچگی APK بدون دانلود |

---

## بعد از اینکه بیلد سبز شد

اگر بیلد **قرمز** شد، لاگ کامل در artifact با نام `build-log` است و
خلاصه‌ی ۶۰ خط آخر خطاها مستقیماً در صفحه‌ی Summary همان اجرا نمایش داده
می‌شود (نیازی به دانلود نیست).

اگر **سبز** شد، artifact با نام `vinabot-apk` شامل فایل APK و
`apk.sha256` است.
