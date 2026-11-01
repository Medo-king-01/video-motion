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
| `itshover_import.py` | يستورد مكوّنات itshover المنسوخة (٢٦٣) ويحوّلها geometry للمحركين | `python3 tools/itshover_import.py --list` |
| `icons_sheet.py` | شيت مراجعة بصري لكل الأيقونات (المحرك P) | `python3 tools/icons_sheet.py --group itshover --limit 24` |
| `icons_preview.mjs` | نفس الشيت بس من رسّام المحرك K (Canvas/Chromium) | `node tools/icons_preview.mjs --limit 24` |
| `motion_studio.html` | استوديو الحركة الأوفلاين: محرر تايملاين JSON + سكرَب + قيم لحظية | `python3 -m http.server 8080` ثم `/tools/motion_studio.html` |
| `theatre_import.py` | يحوّل Theatre.js state export لتايملاين المحركين | `python3 tools/theatre_import.py state.json --offset 18.5` |
| `presenter_build.py` | يقص صور ميدو من الخلفية ويطبّعها ويكتب `assets/poses/poses.json` | `python3 tools/presenter_build.py --sheet cache/poses-sheet.png` |
| `sfx_kit.py` | مكتبة المؤثرات البرمجية: `--list` · `--bank` · `--demo` · `--cues` (ميكس مع التعليق، طوله = طول الـVO) |
| `vo_length.py` | **مصدر الطول الوحيد**: مدة التعليق الصوتي + حدود المشاهد من السكتات + `--check` للمشروع | `python3 tools/vo_length.py out/vo24.wav --json plan/beats.json` |
| `transitions_sheet.py` | شيت مراجعة + كليب معاينة لكل انتقال (بصوته) |
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
make icons      # يعيد بناء الأيقونات + شيت مراجعة
make studio     # استوديو الحركة على :8080
make poses      # قص وضعيات ميدو + شيت مراجعة
make sfx        # معاينة مكتبة المؤثرات (cache/sfx-demo.mp3)
make transitions # شيت + كليب لكل انتقال
make clean      # مسح الكاش ومخرجات الرندر
```

## ملاحظات

- كل الأدوات read-only في الفحص، ومابتكتبش بره مجلد المشروع.
- لو `ffmpeg` مش على الـPATH، المحركات بتحترم `FFMPEG_BIN=/path/to/ffmpeg`.
- `chromium.mjs --check` بيطبع `CHROMIUM_OK <version>` لو المتصفح بيشتغل فعلاً.
