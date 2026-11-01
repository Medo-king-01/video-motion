# tools — أدوات الاستوديو

كل أداة ليها أمر واحد واضح، وكلها من الجذر (repo root).

| الأداة | بتعمل إيه | مثال |
|---|---|---|
| `setup.sh` | بتثبت كل الناقص: python deps (من `requirements.txt`) · ffmpeg · بديل ffprobe · خطوط Cairo · كروميوم | `bash tools/setup.sh` |
| `doctor.py` | تقرير READY / DEGRADED / BLOCKED لكل قدرة، بسبب واضح | `python3 tools/doctor.py` |
| `selftest.py` | اختبار كامل: doctor + unit tests + رندر حقيقي من المحركين | `python3 tools/selftest.py` |
| `new_project.py` | سكافولد مشروع (مدخلات + مجلدات + خط + محرك) | `python3 tools/new_project.py my-reel --engine p` |
| `ffprobe_shim.py` | بديل `ffprobe` متوافق (JSON) مبني على PyAV — لأن FFmpeg الستاتيك بييجي من غير ffprobe | `ffprobe -v error -show_streams -of json in.mp4` |
| `ci.sh` | نفس اللي الـCI بيعمله: ruff + pytest + تدقيق البراند | `bash tools/ci.sh` |
| `chromium.mjs` | كروميوم جاهز لمحرك K من غير CDN بتاع Playwright | `eval "$(node tools/chromium.mjs --env)"` |
| `toolkit/` | اعتماديات Node (`playwright-core`, `@sparticuz/chromium`, خطوط OFL) | `cd tools/toolkit && npm install` |
| `bin/` | روابط ffmpeg/ffprobe اللي بيعملها `setup.sh` (مش متتبعة في git) | — |

## اختصارات

```bash
make setup      # تثبيت
make doctor     # فحص
make test       # اختبارات وحدات (~3 ثواني)
make ci         # lint + tests + تدقيق براند
make selftest   # فحص كامل + رندر
make new SLUG=my-reel ENGINE=p
make clean      # مسح الكاش ومخرجات الرندر
```

## ملاحظات

- كل الأدوات read-only في الفحص، ومابتكتبش بره مجلد المشروع.
- لو `ffmpeg` مش على الـPATH، المحركات بتحترم `FFMPEG_BIN=/path/to/ffmpeg`.
- `chromium.mjs --check` بيطبع `CHROMIUM_OK <version>` لو المتصفح بيشتغل فعلاً.
