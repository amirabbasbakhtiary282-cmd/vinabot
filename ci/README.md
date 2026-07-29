# چرا این فایل اینجاست و نه در .github/workflows/

توکن دسترسی من اجازه‌ی نوشتن روی فایل‌های `.github/workflows/` را ندارد
(GitHub این را برای هر GitHub App بدون مجوز `workflows` مسدود می‌کند):

```
refusing to allow a GitHub App to create or update workflow
`.github/workflows/build.yml` without `workflows` permission
```

بنابراین نسخه‌ی به‌روزشده‌ی workflow اینجا گذاشته شده تا **شما** آن را
اعمال کنید.

## چه چیزی تغییر کرده؟

1. **اجرا روی این شاخه**: `branches: [main, master, 'arena/**']` و
   `pull_request` — بدون این، APK فقط بعد از merge ساخته می‌شود، در حالی
   که قرار شد **قبل** از merge تست کنیم.
2. **مرحله‌ی تست قبل از بیلد**: ۷۰ تست واحد + pyflakes + compileall.
   بیلد APK حدود ۱-۳ ساعت طول می‌کشد؛ بی‌معنی است که با یک خطای نگارشی
   ساده آن همه زمان تلف شود.
3. **کش buildozer**: بیلدهای بعدی بسیار سریع‌تر می‌شوند.
4. **خلاصه‌ی خطا**: در صورت شکست، ۴۰ خط آخر خطاها مستقیم در صفحه‌ی
   Summary نمایش داده می‌شود (نیازی به دانلود کل build.log نیست).

## چطور اعمال کنم؟

```bash
git checkout arena/019faf15-vinabot
cp ci/build-apk.proposed.yml .github/workflows/build.yml
git add .github/workflows/build.yml
git commit -m "CI: run tests before APK build, build on arena branches"
git push origin arena/019faf15-vinabot
```

بعد از این push، بیلد APK **به‌صورت خودکار** روی همین شاخه شروع می‌شود.

## راه جایگزین (بدون تغییر فایل)

اگر نمی‌خواهید workflow را تغییر دهید، می‌توانید یک بار دستی اجرا کنید:

```
Actions → Build APK → Run workflow → Branch: arena/019faf15-vinabot
```

(این کار به لطف `workflow_dispatch` که از قبل در فایل هست ممکن است.)
