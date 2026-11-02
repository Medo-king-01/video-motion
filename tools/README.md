# tools — أدوات الاستوديو

كل أداة ليها أمر واحد واضح، وكلها من الجذر (repo root).

| الأداة | بتعمل إيه | مثال |
|---|---|---|
| `setup.sh` | بتثبت كل الناقص: python deps (من `requirements.txt`) · ffmpeg · بديل ffprobe · الخطوط (٢١ عيلة OFL) · كروميوم | `bash tools/setup.sh` |
| `doctor.py` | تقرير READY / DEGRADED / BLOCKED لكل قدرة، بسبب واضح | `python3 tools/doctor.py` |
| `selftest.py` | اختبار كامل: doctor + unit tests + رندر P/K؛ `--remotion` يضيف R منفردًا، و`--hybrid` يرندر ويجمع P/K/R + صوت end-to-end | `python3 tools/selftest.py --hybrid` |
| `render_hybrid.py` | يرندر مخطط `plan/hybrid.json`: يتحقق من مقاطع P/K/R المتتابعة، ثم يوحّد الفيديو ويضيف الصوت مرة واحدة | `python3 ../../tools/render_hybrid.py --project .` من جذر المشروع |
| `render_p_segment.py` | adapter داخلي لرندر مدى إطارات محدد من P بصيغة الفيديو المشتركة | يستخدمه `render_hybrid.py` |
| `new_project.py` | سكافولد مشروع (مدخلات + مجلدات + خط + محرك P/K/R) | `python3 tools/new_project.py my-reel --engine r` |
| `ffprobe_shim.py` | بديل `ffprobe` متوافق (JSON) مبني على PyAV — لأن FFmpeg الستاتيك بييجي من غير ffprobe | `ffprobe -v error -show_streams -of json in.mp4` |
| `ci.sh` | نفس اللي الـCI بيعمله: ruff + pytest + تدقيق البراند | `bash tools/ci.sh` |
| `chromium.mjs` | كروميوم مشترك لمحركَي K وR، من غير تنزيلات متصفح من CDN | `eval "$(node tools/chromium.mjs --env)"` |
| `itshover_import.py` | يستورد مكوّنات itshover المنسوخة (٢٦٣) ويحوّلها geometry للمحركين | `python3 tools/itshover_import.py --list` |
| `icons_sheet.py` | شيت مراجعة بصري لكل الأيقونات (المحرك P) | `python3 tools/icons_sheet.py --group itshover --limit 24` |
| `icons_preview.mjs` | نفس الشيت بس من رسّام المحرك K (Canvas/Chromium) | `node tools/icons_preview.mjs --limit 24` |
| `motion_studio.html` | استوديو الحركة الأوفلاين: محرر تايملاين JSON + سكرَب + قيم لحظية | `python3 -m http.server 8080` ثم `/tools/motion_studio.html` |
| `theatre_import.py` | يحوّل Theatre.js state export لـJSON الحركة المشتركة لـP/K/R | `python3 tools/theatre_import.py state.json --offset 18.5` |
| `presenter_build.py` | يقص صور ميدو من الخلفية ويطبّعها ويكتب `assets/poses/poses.json` | `python3 tools/presenter_build.py --sheet cache/poses-sheet.png` |
| `sfx_kit.py` | مكتبة المؤثرات البرمجية: `--list` · `--bank` · `--demo` · `--cues` (ميكس مع التعليق، طوله = طول الـVO) · `--grid` (cue sheet على شبكة الـBPM) |
| `vo_length.py` | **مصدر الطول الوحيد**: مدة التعليق الصوتي + حدود المشاهد من السكتات + `--bpm` يزحزح القطع للشبكة + `--check` للمشروع | `python3 tools/vo_length.py out/vo24.wav --json plan/beats.json` |
| `whisper_fetch.py` | تنزيل موديل Whisper-small CT2 int8 من npm (بديل أوفلاين لـHF/Azure المحجوبين) + تحقق SHA-256 | `python3 tools/whisper_fetch.py --out .cache/whisper-small-ct2-int8` |
| `whisper_align.py` | تفريغ محلي بـfaster-whisper → كلمات بتوقيتات **مقاسة** من الـWAV (JSON) | `python3 tools/whisper_align.py vo.wav --model .cache/whisper-small-ct2-int8 --out cache/words.json --no-vad` |
| `caption_align.py` | محاذاة الكلمات على السكريبت (DP) + سناب للسكتات + hold لحد الكلمة الجاية + إخراج كابشن و`data.js` | `python3 tools/caption_align.py --scenes plan/script-scenes.json --vo vo.wav --model .cache/whisper-small-ct2-int8 --out-dir src` |
| `text_animations_import.py` | يستورد ٥١ حركة نص من مرجع ريلز ويحوّلها مسارات حركة رقمية (K/P/R) + مولّد أنماط كابشن، معاد تلوينها للبراند ومن غير صناديق | `python3 tools/text_animations_import.py --html reels_text_animations.html` |
| `text_direction.py` | يتحقق/يهيّئ خطة حركة **كل نص ظاهر** اللي الوكيل بيختارها لكل مشهد (`plan/text-direction.json` v2 + تغطية `copy.json`) — مفيش style افتراضي | `python3 tools/text_direction.py projects/<slug> --init` ثم `--check` |
| `medo-motion/scripts/analyze_ref.py` | تحليل مرجع محليًا: شيتات مؤرخة، حركة، palette تقريبية، إيقاع قطع وصوت؛ لا ينقل ألوان المرجع للهوية | `python3 medo-motion/scripts/analyze_ref.py ref.mp4 --dur 15 --out cache/ref` |
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

- **محاذاة الكابشن المقاسة**: خط أوفلاين كامل (whisper_fetch → whisper_align → caption_align) موثّق في `docs/alignment.md`. اعتمادياته اختيارية: `pip install -r tools/requirements-align.txt`.
- كل الأدوات read-only في الفحص، ومابتكتبش بره مجلد المشروع.
- لو `ffmpeg` مش على الـPATH، المحركات بتحترم `FFMPEG_BIN=/path/to/ffmpeg`.
- `chromium.mjs --check` بيطبع `CHROMIUM_OK <version>` لو المتصفح بيشتغل فعلاً.
