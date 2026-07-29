// -*- coding: utf-8 -*-
//
// vina_llm.cpp - لایه‌ی پل ساده و پایدار (C ABI) روی llama.cpp
//
// چرا این فایل وجود دارد؟
// -------------------------------------------------------------------------
// llama-cpp-python (پکیج پایتونی رایج برای اجرای مدل‌های GGUF) به دلایل
// زیر برای اندروید/python-for-android مناسب نیست:
//   - به Cython/CFFI با ساختارهای پیچیده‌ی C++ وابسته است که به‌صورت
//     پایدار روی NDK اندروید کراس‌کامپایل نمی‌شود.
//   - نسخه‌ی llama.cpp داخل آن معمولاً از نسخه‌ی بالادستی عقب‌تر است.
//   - نصب آن از طریق pip روی p4a نیاز به چرخه‌ی build کامل CMake+setuptools
//     دارد که در محیط کراس‌کامپایل اندروید بسیار شکننده است.
//
// راه‌حل: به‌جای آن، مستقیماً از سورس رسمی llama.cpp (که خودش با CMake و
// NDK toolchain اندروید به‌طور رسمی و پایدار کراس‌کامپایل می‌شود) دو
// کتابخانه‌ی libllama.so و libggml*.so را می‌سازیم، و یک لایه‌ی نازک با
// امضای تابع ساده (فقط انواع پایه: int/float/char*) روی آن قرار می‌دهیم.
// این امضای ساده از طریق ctypes در پایتون به‌سادگی و بدون نیاز به کامپایل
// هیچ افزونه‌ی پایتونی (extension module) قابل استفاده است.

#include "llama.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <atomic>
#include <algorithm>

extern "C" {

struct vina_llm_ctx {
    llama_model*         model  = nullptr;
    llama_context*       ctx    = nullptr;
    const llama_vocab*   vocab  = nullptr;
    int                  n_ctx  = 0;
    int                  n_batch = 512;
    std::string          last_error;
};

#if defined(_WIN32)
#define VINA_API __declspec(dllexport)
#else
#define VINA_API __attribute__((visibility("default")))
#endif

static void vina_null_log_callback(enum ggml_log_level level, const char* text, void* user_data) {
    (void)level; (void)text; (void)user_data; // بی‌صدا کردن لاگ‌های پرحجم llama.cpp روی موبایل
}

VINA_API void vina_llm_backend_init() {
    llama_backend_init();
}

VINA_API void vina_llm_set_verbose(int verbose) {
    if (verbose) {
        llama_log_set(nullptr, nullptr); // بازگرداندن رفتار پیش‌فرض (چاپ در stderr)
    } else {
        llama_log_set(vina_null_log_callback, nullptr);
    }
}

VINA_API void vina_llm_backend_free() {
    llama_backend_free();
}

VINA_API int vina_llm_get_cpu_count() {
    // llama.cpp doesn't expose a direct helper; caller supplies thread count,
    // this remains here for potential future use / symmetry.
    return 0;
}

static void copy_error(vina_llm_ctx* h, const char* msg, char* err_buf, int err_buf_size) {
    if (h) h->last_error = msg;
    if (err_buf && err_buf_size > 0) {
        std::snprintf(err_buf, err_buf_size, "%s", msg);
    }
}

VINA_API vina_llm_ctx* vina_llm_load(const char* model_path, int n_ctx, int n_threads,
                                      char* err_buf, int err_buf_size) {
    if (!model_path || !*model_path) {
        copy_error(nullptr, "model_path is empty", err_buf, err_buf_size);
        return nullptr;
    }

    llama_model_params mparams = llama_model_default_params();
    mparams.n_gpu_layers = 0; // فقط CPU؛ برای سازگاری حداکثری با گوشی‌ها

    llama_model* model = llama_model_load_from_file(model_path, mparams);
    if (!model) {
        char buf[512];
        std::snprintf(buf, sizeof(buf), "بارگذاری مدل از مسیر ناموفق بود: %s", model_path);
        copy_error(nullptr, buf, err_buf, err_buf_size);
        return nullptr;
    }

    const llama_vocab* vocab_tmp = llama_model_get_vocab(model);
    (void)vocab_tmp;

    llama_context_params cparams = llama_context_default_params();
    uint32_t requested_ctx = n_ctx > 0 ? (uint32_t)n_ctx : 2048u;

    // برخی معماری‌ها (مثل GPT-2 با absolute position embedding) اگر context
    // بزرگ‌تر از مقداری که مدل با آن train شده درخواست شود، هنگام دسترسی به
    // جدول position embedding با سرریز ایندکس کرش می‌کنند. مدل‌های مبتنی بر
    // RoPE (مثل Llama/Qwen/Gemma/Phi که برای وینا هدف اصلی هستند) این
    // محدودیت را ندارند، اما برای ایمنی کامل و جلوگیری از کرش با هر مدلی،
    // همیشه به سقف واقعی مدل (n_ctx_train) محدود می‌کنیم.
    int32_t n_ctx_train = llama_model_n_ctx_train(model);
    if (n_ctx_train > 0 && requested_ctx > (uint32_t)n_ctx_train) {
        requested_ctx = (uint32_t)n_ctx_train;
    }
    cparams.n_ctx = requested_ctx;

    // n_batch نباید از n_ctx بزرگ‌تر باشد (وگرنه برخی معماری‌ها مثل GPT-2 که
    // از absolute position embedding استفاده می‌کنند با سرریز ایندکس کرش
    // می‌کنند)، و نباید از n_ctx خیلی بزرگ‌تر هم باشد چون مصرف حافظه‌ی
    // compute buffer را بالا می‌برد. سقف ۵۱۲ برای گوشی‌های معمولی مناسب است.
    uint32_t batch_size = requested_ctx < 512u ? requested_ctx : 512u;
    cparams.n_batch = batch_size;
    cparams.n_ubatch = batch_size;
    cparams.n_threads = n_threads > 0 ? n_threads : 4;
    cparams.n_threads_batch = cparams.n_threads;

    llama_context* ctx = llama_init_from_model(model, cparams);
    if (!ctx) {
        copy_error(nullptr, "ساخت context ناموفق بود (احتمالاً حافظه کافی نیست)", err_buf, err_buf_size);
        llama_model_free(model);
        return nullptr;
    }

    vina_llm_ctx* handle = new vina_llm_ctx();
    handle->model = model;
    handle->ctx = ctx;
    handle->vocab = llama_model_get_vocab(model);
    handle->n_ctx = (int)cparams.n_ctx;
    handle->n_batch = (int)cparams.n_batch;
    return handle;
}

VINA_API void vina_llm_free(vina_llm_ctx* handle) {
    if (!handle) return;
    if (handle->ctx) llama_free(handle->ctx);
    if (handle->model) llama_model_free(handle->model);
    delete handle;
}

VINA_API int vina_llm_n_ctx(vina_llm_ctx* handle) {
    return handle ? handle->n_ctx : 0;
}

VINA_API void vina_llm_reset_context(vina_llm_ctx* handle) {
    // پاک‌سازی حافظه‌ی مکالمه (KV cache) بین مکالمات جدید، تا context قبلی
    // به‌اشتباه به مکالمه‌ی بعدی نشت نکند و مصرف حافظه رشد نامحدود نداشته باشد.
    if (!handle || !handle->ctx) return;
    llama_kv_self_clear(handle->ctx);
}

// تخمین تعداد توکن‌های یک متن؛ برای تصمیم‌گیری درباره‌ی برش تاریخچه در سمت پایتون.
VINA_API int vina_llm_count_tokens(vina_llm_ctx* handle, const char* text) {
    if (!handle || !handle->vocab || !text) return -1;
    int n = -llama_tokenize(handle->vocab, text, (int)strlen(text), nullptr, 0, true, true);
    return n;
}

// تولید پاسخ برای `prompt`. نتیجه به‌صورت رشته‌ی UTF-8 در out_buf نوشته می‌شود.
// `cancel_flag` یک اشاره‌گر اختیاری به یک int است: اگر در حین تولید به مقدار
// غیرصفر تغییر کند، تولید متوقف می‌شود (برای دکمه‌ی «لغو» در رابط کاربری).
// بازگشت: تعداد بایت نوشته‌شده (>= 0) یا کد خطای منفی.
// نسخه‌ی جریانی (streaming): هر قطعه‌ی متن تولیدشده بلافاصله از طریق
// `token_cb` به سمت پایتون داده می‌شود تا رابط کاربری بتواند توکن‌به‌توکن
// نمایش دهد و موتور TTS بتواند جمله‌به‌جمله شروع به خواندن کند (بدون
// انتظار برای پایان کل پاسخ). اگر callback مقدار غیرصفر برگرداند، تولید
// متوقف می‌شود (برای قطع کردن وسط صحبت / barge-in).
typedef int (*vina_token_cb)(const char* piece, void* user_data);

VINA_API int vina_llm_generate_stream(vina_llm_ctx* handle, const char* prompt,
                                int max_tokens, float temperature, float top_p, int top_k,
                                float repeat_penalty, const char* stop_str,
                                char* out_buf, int out_size,
                                volatile int* cancel_flag,
                                vina_token_cb token_cb, void* user_data);

VINA_API int vina_llm_generate(vina_llm_ctx* handle, const char* prompt,
                                int max_tokens, float temperature, float top_p, int top_k,
                                float repeat_penalty, const char* stop_str,
                                char* out_buf, int out_size,
                                volatile int* cancel_flag) {
    // نسخه‌ی قدیمی و blocking صرفاً حالت خاصی از نسخه‌ی جریانی است
    // (بدون callback) تا منطق تولید فقط در یک جا نگه‌داری شود.
    return vina_llm_generate_stream(handle, prompt, max_tokens, temperature, top_p,
                                     top_k, repeat_penalty, stop_str, out_buf,
                                     out_size, cancel_flag, nullptr, nullptr);
}

VINA_API int vina_llm_generate_stream(vina_llm_ctx* handle, const char* prompt,
                                int max_tokens, float temperature, float top_p, int top_k,
                                float repeat_penalty, const char* stop_str,
                                char* out_buf, int out_size,
                                volatile int* cancel_flag,
                                vina_token_cb token_cb, void* user_data) {
    if (!handle || !handle->ctx || !handle->vocab) return -1;
    if (!prompt) return -2;

    const llama_vocab* vocab = handle->vocab;
    llama_context* ctx = handle->ctx;

    int n_prompt = -llama_tokenize(vocab, prompt, (int)strlen(prompt), nullptr, 0, true, true);
    if (n_prompt <= 0) {
        copy_error(handle, "توکنایز کردن ورودی ناموفق بود", nullptr, 0);
        return -3;
    }

    // اگر طول prompt از ظرفیت context بیشتر باشد، خطای واضح برگردان (به‌جای
    // کرش یا رفتار نامشخص) تا سمت پایتون بتواند تاریخچه را کوتاه‌تر کند.
    if (n_prompt >= handle->n_ctx) {
        copy_error(handle, "متن ورودی از ظرفیت حافظه‌ی مدل بزرگتر است", nullptr, 0);
        return -4;
    }

    std::vector<llama_token> tokens(n_prompt);
    if (llama_tokenize(vocab, prompt, (int)strlen(prompt), tokens.data(),
                        (int)tokens.size(), true, true) < 0) {
        copy_error(handle, "توکنایز کردن ورودی ناموفق بود (مرحله دوم)", nullptr, 0);
        return -5;
    }

    // پردازش پرامپت به‌صورت دسته‌ای (chunk) با اندازه‌ی حداکثر n_batch، چون
    // llama_decode برای دسته‌ای بزرگ‌تر از n_batch با abort مواجه می‌شود.
    int n_batch = handle->n_batch > 0 ? handle->n_batch : 512;
    for (int offset = 0; offset < (int)tokens.size(); offset += n_batch) {
        int chunk_size = std::min(n_batch, (int)tokens.size() - offset);
        llama_batch batch = llama_batch_get_one(tokens.data() + offset, chunk_size);
        if (llama_decode(ctx, batch) != 0) {
            copy_error(handle, "پردازش اولیه‌ی متن ورودی (decode) ناموفق بود", nullptr, 0);
            return -6;
        }
    }

    llama_sampler_chain_params sparams = llama_sampler_chain_default_params();
    llama_sampler* smpl = llama_sampler_chain_init(sparams);

    if (repeat_penalty > 1.0f) {
        llama_sampler_chain_add(smpl, llama_sampler_init_penalties(64, repeat_penalty, 0.0f, 0.0f));
    }

    if (temperature > 0.0f) {
        if (top_k > 0) llama_sampler_chain_add(smpl, llama_sampler_init_top_k(top_k));
        if (top_p > 0.0f && top_p < 1.0f) llama_sampler_chain_add(smpl, llama_sampler_init_top_p(top_p, 1));
        llama_sampler_chain_add(smpl, llama_sampler_init_temp(temperature));
        llama_sampler_chain_add(smpl, llama_sampler_init_dist(LLAMA_DEFAULT_SEED));
    } else {
        llama_sampler_chain_add(smpl, llama_sampler_init_greedy());
    }

    std::string result;
    std::string stop_seq = stop_str ? stop_str : "";
    int generated = 0;

    // ----------------------------------------------------------------
    // مدیریت ارسال جریانی
    // ----------------------------------------------------------------
    // `emitted` تعداد بایت‌هایی از `result` است که قبلاً به callback داده شده.
    // دو نکته‌ی مهم:
    //  1) یک توکن llama.cpp ممکن است فقط بخشی از یک کاراکتر UTF-8 باشد
    //     (خیلی رایج در فارسی/عربی). اگر آن بایت‌های ناقص را جداگانه به
    //     پایتون بدهیم، decode خراب می‌شود. پس فقط تا آخرین مرز کامل
    //     UTF-8 ارسال می‌کنیم.
    //  2) اگر stop sequence داریم، باید انتهای رشته را به اندازه‌ی
    //     (len(stop)-1) بایت نگه داریم تا اگر بخشی از stop بود، به‌اشتباه
    //     به کاربر نمایش داده نشود.
    size_t emitted = 0;
    bool   cb_stop = false;

    // آخرین ایندکسی که یک کاراکتر کامل UTF-8 در آن تمام می‌شود را برمی‌گرداند.
    auto utf8_safe_end = [](const std::string& s, size_t limit) -> size_t {
        size_t end = limit;
        while (end > 0) {
            unsigned char c = (unsigned char)s[end - 1];
            if ((c & 0x80) == 0x00) return end;              // ASCII: مرز کامل
            if ((c & 0xC0) == 0x80) { end--; continue; }     // بایت ادامه: عقب برو
            // بایت شروع یک دنباله‌ی چندبایتی: بررسی کن آیا کامل است
            size_t need = (c & 0xE0) == 0xC0 ? 2 : (c & 0xF0) == 0xE0 ? 3 : 4;
            return (limit - (end - 1)) >= need ? limit : end - 1;
        }
        return 0;
    };

    auto flush_stream = [&](bool final_flush) {
        if (!token_cb || cb_stop) return;
        size_t keep_back = final_flush || stop_seq.empty() ? 0 : stop_seq.size() - 1;
        if (result.size() <= emitted + keep_back) return;
        size_t limit = result.size() - keep_back;
        size_t safe = final_flush ? limit : utf8_safe_end(result, limit);
        if (safe <= emitted) return;
        std::string chunk = result.substr(emitted, safe - emitted);
        emitted = safe;
        if (token_cb(chunk.c_str(), user_data) != 0) cb_stop = true;
    };

    for (int i = 0; i < max_tokens; i++) {
        // توقف یا با پرچم لغو از بیرون (دکمه‌ی توقف / قطع کردن صحبت)، یا با
        // درخواست خود callback.
        if ((cancel_flag && *cancel_flag) || cb_stop) {
            break;
        }

        llama_token new_token = llama_sampler_sample(smpl, ctx, -1);

        if (llama_vocab_is_eog(vocab, new_token)) {
            break;
        }

        char piece_buf[256];
        int n = llama_token_to_piece(vocab, new_token, piece_buf, sizeof(piece_buf), 0, true);
        if (n > 0) {
            if ((int)result.size() + n < out_size - 1) {
                result.append(piece_buf, n);
                generated++;
            } else {
                break; // بافر خروجی پر شد
            }
        }

        if (!stop_seq.empty() && result.size() >= stop_seq.size()) {
            if (result.compare(result.size() - stop_seq.size(), stop_seq.size(), stop_seq) == 0) {
                result.resize(result.size() - stop_seq.size());
                // چیزی که تا اینجا ارسال نشده و جزو stop نیست را بفرست
                if (emitted > result.size()) emitted = result.size();
                flush_stream(true);
                break;
            }
        }

        // ارسال قطعه‌ی جدید به سمت پایتون (نمایش زنده + شروع TTS)
        flush_stream(false);

        // اگر context در حال پر شدن است، به‌جای کرش، تولید را متوقف کن.
        if (llama_kv_self_used_cells(ctx) >= handle->n_ctx - 4) {
            break;
        }

        llama_batch next_batch = llama_batch_get_one(&new_token, 1);
        if (llama_decode(ctx, next_batch) != 0) {
            break;
        }
    }

    // ارسال باقی‌مانده‌ی بافر (بخشی که به‌خاطر keep_back/مرز UTF-8 نگه داشته شده)
    flush_stream(true);

    llama_sampler_free(smpl);

    int len = (int)result.size();
    if (out_buf && out_size > 0) {
        int copy_len = len < out_size - 1 ? len : out_size - 1;
        std::memcpy(out_buf, result.data(), copy_len);
        out_buf[copy_len] = '\0';
        return copy_len;
    }
    return len;
}

VINA_API const char* vina_llm_last_error(vina_llm_ctx* handle) {
    return handle ? handle->last_error.c_str() : "";
}

} // extern "C"
