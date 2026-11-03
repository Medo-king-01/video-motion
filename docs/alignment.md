# محاذاة الكابشن المقاسة (Measured caption alignment)

الكابشن المحروق لازم يظهر **كلمة منطوقة واحدة في كل مرة**، بتوقيت **مقاس من الـWAV نفسه** —
مش تقديري من حدود المشاهد ولا من منتصف السكتات. الملف ده بيوصّف خط الإنتاج اللي اتبنى واتأكد
على تعليق صوتي حقيقي (لهجة مصرية)، وإزاي تعيد استخدامه لأي حلقة.

> القاعدة: `validateWordTimeline` لازم يعدّي لكل مشهد، والتوقيت يتراجع ضد الصوت في فريمات
> مت rendered قبل الاعتماد. انظر `projects/ram-episode-03` كمثال كامل.

## ليه خط أوفلاين؟ (الواقع الشبكي)

في بيئات مقفولة، تنزيل موديلات Whisper من المصادر المعتادة بيفشل:

| المصدر | الحالة |
|---|---|
| `huggingface.co` (صفحة/resolve/api) | ❌ TLS EOF |
| `openaipublic.azureedge.net` (موديلات OpenAI `.pt`) | ❌ TLS EOF |
| GitHub release assets / Git LFS (`objects.githubusercontent.com`, `media.githubusercontent.com`) | ❌ محجوب |
| `registry.npmjs.org` · `pypi.org` · `codeload.github.com` | ✅ متاح |

الحل: ناشر على npm بيوزّع تحويل **CTranslate2 int8** حقيقي لـ**Whisper-small** مقسوم على 4 حزم.
بننزّلها، نركّب `model.bin`, ونتأكد من **SHA-256** قبل الاستخدام. الموديل بيتكتب في كاش
(مش بيتعمله commit — قابل لإعادة البناء من السكربت).

## الأدوات

| الأداة | الوظيفة |
|---|---|
| `tools/whisper_fetch.py` | تنزيل وتركيب موديل Whisper-small CT2 int8 من npm + تحقق SHA-256 |
| `tools/whisper_align.py` | تفريغ محلي بـfaster-whisper → كلمات بتوقيتات مقاسة (JSON) |
| `tools/caption_align.py` | محاذاة DP للكلمات على السكريبت + سناب للسكتات + hold لحد الكلمة الجاية + إخراج موديولات الكابشن و`data.js` |

اعتماديات اختيارية: `pip install -r tools/requirements-align.txt` (`faster-whisper`, `ctranslate2`).
دي مش ضمن `requirements.txt` الأساسي عشان الرندر العادي ما يحتاجهاش.

## خط الإنتاج

```bash
# 1) الموديل (مرة واحدة؛ ~480MB في الكاش)
python3 tools/whisper_fetch.py --out .cache/whisper-small-ct2-int8

# 2) (اختياري) تفريغ كامل للفحص اليدوي
python3 tools/whisper_align.py out/vo24.wav \
    --model .cache/whisper-small-ct2-int8 --out cache/words.json --language ar --no-vad

# 3) الكابشن المقاس لكل المشاهد + خريطة المشاهد
python3 tools/caption_align.py \
    --scenes plan/script-scenes.json \
    --vo assets/vo/episode.wav \
    --model .cache/whisper-small-ct2-int8 \
    --out-dir src --lang ar
```

صيغة `script-scenes.json`: قائمة JSON غير فارغة؛ كل مشهد زي المثال ده (حطّه جوه `[...]`):

```json
{ "id": "S02", "module": "ram-question",
  "text": "بس يا ترى إيه الفرق؟ وأنهي حجم مناسب لاستخدامك؟",
  "words": ["بس","يا","ترى","إيه","الفرق","وأنهي","حجم","مناسب","لاستخدامك"],
  "start": 8.433, "end": 12.358 }
```

- `start/end` بالثواني على توقيت الحلقة الكامل (حدود المشاهد من منتصف السكتات — `tools/vo_length.py`).
- `words` دايمًا قائمة كلمات السكريبت (strings)، أو بتتشتق من `text.split()` لو مش موجودة.
- `--freeze S01` محتاج `final` في مشهد S01: قائمة `{text,start,end}` بتوقيت **محلي للمشهد**، مش الحلقة.
  النصوص لازم تطابق `words` بعد تطبيع التشكيل/علامات الترقيم وبنفس الترتيب، والتوقيت محدود بمدة المشهد ومن غير تداخل. مثال:
  `"final": [{"text":"قبل","start":0.12,"end":0.6}]` مع `"words":["قبل"]`.
  تقدر تستخدم `cache/scene-measurements.json` الناتج كمدخل للتشغيل اللي بعده وتجمّد مشاهد منه.
  لو كل المشاهد frozen، مش محتاج `--model` أو حزم Whisper.
- `id` معرف ASCII يبدأ بحرف (حروف/أرقام/`_`/`-`)، و`module` slug إنجليزي صغير؛ ممنوع المسارات والمعرفات المكررة.
- الصوت لازم **mono PCM16 WAV**؛ stereo وأي عمق عينة تاني بيترفضوا قبل القص.
  للتحويل: `ffmpeg -i input.wav -ac 1 -ar 24000 -c:a pcm_s16le episode.wav`.
- حدود المشاهد مرتبة وغير متداخلة وجوه مدة الصوت. لو ASR ماطلعش كلمات مطابقة، الأداة بتوقف بخطأ واضح؛
  مش بتخترع توقيتات. راجع الصوت/اللغة/الموديل قبل إعادة المحاولة.
- الناتج: `src/captions-sXX.js` (موديول لكل مشهد) + `src/data.js` + `cache/scene-measurements.json`.

## دروس اتأكدت عمليًا (مهمة للجودة)

1. **اقفل VAD على الشرايح القصيرة** (`vad_filter=False`): الـVAD بيسقط كلام حقيقي عند أطراف الشريحة.
2. **الـprompt الحرفي ممكن يقفز البداية**: لو `initial_prompt` = نص المشهد بالظبط، Whisper ساعات بيتجاهل أول
   كلمات. الحل: إعادة محاولة من غير prompt مع `temperature=(0.0,0.2,0.4)` و`repetition_penalty=1.15`.
3. **الأرقام المنطوقة**: السكريبت "32" ممكن تتنطق "اتنين وتلاتين". محاذاة DP بتربطهم بالرقم؛
   التطبيع بيوحد الألف/التاء المربوطة/الياء ويشيل التشكيل والعلامات.
4. **ترتيب الكلمات**: الـASR ممكن يعكس كلمتين محليًا. `snap_and_hold` بيفرز بالـonset وبيفرض
   ترتيب تصاعدي صارم، وكل كلمة بتفضل ظاهرة لحد ما اللي بعدها تبدأ.
5. **سناب البداية**: لو onset وقع في سكتة قبل الكلام، بيتزحزح لبداية النشاط المقاس (RMS envelope 20ms).
6. **حدود المشاهد**: اتأكد إن القطع في سكتة حقيقية مش جوه كلمة. (في الحلقة 03، قطع S09/S10 اتصحح لـ67.0s
   لأن القطع القديم كان جوه كلام S10.)

## الصوت وQC (بعد الرندر)

- **الميكس**: `tools/sfx_kit.py --cues ... --vo ... --out mix.wav` (المدة = طول الـVO).
- **Loudness**: هدّف **−14.5 ±0.3 LUFS** و**true peak ≤ −1.5 dBTP**. استخدم **two-pass loudnorm**
  (قياس `print_format=json` ثم تطبيق بـ`measured_*` + `linear=true`). الـvolume-only أو المرور الواحد
  بيفشلوا لما الـTP سخن.
- **فخ AAC**: ترميز AAC بيرفع الـtrue peak شوية فوق الماستر (مثلاً −1.49 → −1.42). الحل: اعمل
  re-master بـ**true-peak limiter** (هدف `TP=-1.8`) وسيب الـLUFS عند −14.5، ثم رمّز الصوت. لو الفيديو
  اترندر خلاص، **انسخ الفيديو وأعد ترميز الصوت بس** (`-c:v copy -c:a aac`) من غير إعادة رندر.
- **Bitrate**: الرندر الرسومي الخفيف بيقع تحت بوابة ≥2.5 Mbps عند CRF 18. استخدم **`--crf 12`**
  (أضيف لقالب الرندر `medo-motion/templates/render/render.js`).
- **المدة**: عدد الفريمات = `ceil(duration×fps)`؛ الفيديو بيبقى أطول من الـVO بكسر فريم — ده مقبول.

## الاختبارات

```bash
python3 -m pytest tests/test_caption_align.py   # الدوال النقية من غير موديل
```

بتغطي: التطبيع العربي، محاذاة DP (مطابقة/فجوات/أرقام)، كشف النشاط، السناب+hold+الترتيب، وإخراج الموديولات.
