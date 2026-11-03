# HyperFrames: ملاءمته لاستوديو ميدو

**مراجعة:** 2026-11-04 · **المصدر:** https://github.com/heygen-com/hyperframes · **النسخة:** CLI `0.9.9` (المستودع: Apache-2.0، آخر دفع 2026-11-03)

مراجعة ملاءمة، مش شهادة أمنية. اتجرّب فعليًا: تثبيت، `init`، `lint`، `check`، و`render` على
composition عربي ١٠٨٠×١٩٢٠ بخط Cairo من `assets/fonts/`. لم يُنقل كود ولا أصول إلى الاستوديو.

## الفكرة | What it is

HyperFrames محرك **HTML ← فيديو**: بتكتب صفحة HTML/CSS وبتدي عناصرها `data-start`/`data-duration`،
والـruntime بيسأل عن فريم واحد في المرة (`seekFrame`) ويلتقطه بـChrome ثم يرمّزه بـFFmpeg.
المنطق قريب جدًا من محرك **K** عندنا: نفس المنتج النهائي (headless browser + FFmpeg + seek)،
بس واجهة التأليف عندهم **HTML + GSAP** بدل canvas 2D + `motion/*` API.

الحزمة مقسومة: `core` (runtime + adapters) · `engine`/`producer` (Puppeteer + FFmpeg) ·
`lint` (١٤٥ قاعدة) · `player` · `shader-transitions` · `cli` · `studio` (تطبيق سطح مكتب).

## اللي اتقاس فعلًا

| الاختبار | النتيجة |
|---|---|
| التثبيت | `npm i hyperframes@0.9.9` → ٧٨ حزمة، ١١ ثانية، ~٢٤ MB (بلا Chromium/FFmpeg) |
| `hyperframes lint` على composition عربي | ٠ خطأ، ١ تحذير (`timeline_track_too_dense`: ٤ عناصر على track واحد) |
| `hyperframes check` | Layout ٠ · Motion ٠ · **Contrast ١٤/١٤ WCAG AA** · Craft تحذير واحد (`first_frame_empty`) |
| الرندر | ٤ث / ١٢٠ فريم ١٠٨٠×١٩٢٠ في **٨.١ ثانية** على نواتين (screenshot capture، software GL) |
| الحتمية | `png-sequence` مرتين → **١٢٠/١٢٠ فريم متطابق بكسل-ببكسل**؛ الـmp4 فرق ≤١ في ٩٥/١٢٠ فريم (المُرمِّز، مش التخطيط) |
| العربي | اتشكّل صح (Cairo، `dir="rtl"`، `text-align: right`) — مفيش كسر حروف ولا ترتيب مقلوب |
| الشبكة | الـCDN وGoogle Fonts **مسدودين** هنا: لازم `gsap.min.js` وملفات الخطوط تتنسخ محلّيًا، وإلا الرندر يفشل بـ`sub_timeline_script_failure` |
| السجل (registry) | ٤٥٦ عنصرًا (٢٣٨ component + ٢١٠ block) — `add` فشل بدون شبكة |

## ليه **مش** نتبنّاه كمحرك رندر

1. **بيحلّ مشكلة مش عندنا.** عندنا تلات محركات P/K/R + Hybrid، محكومة بالـVO، متكافئة في التوقيت،
   ولها شبكة إيقاع و`space3d` و`backgrounds` و`techniques` مقاسة. HyperFrames هيبدأ من الصفر
   في كل ده في مقابل واجهة تأليف HTML — مش ميزة للاستوديو.
2. **الخط الأحمر بتاع الهوية.** الـline الافتراضي بيوقع `cdn.jsdelivr.net` وGoogle Fonts (٥٧٥ ملف
   HTML في الـregistry بيستدعي jsDelivr)، والـblocks فيها بالِتاتها وخطوطها. ده عكس قاعدة
   «كل لون من `brand.json`، مفيش hex بره البالِت» و«مفيش اتصال شبكي أثناء الرندر».
3. **العربي مش مواطن من الدرجة الأولى.** اتشكّل صح لأن Chrome بيعمله، لكن مفيش عندهم
   `arabic_shape.py` ولا قياس نص عربي ولا قواعد سطر عربي زي `reference/arabic-typography.md`.
   أي ميزة نص عربية هتتكتب عندنا من جديد.
4. **التراخيص مختلطة.** المستودع Apache-2.0، لكن الـblocks بتـvendor **GSAP** بترخيصه القياسي
   (مش OSI) و**three.js** بإصدارات مختلفة (r181/r185/CDN 0.170–0.181). النقل مش نظيف الحقوق.
5. **Node ٢٢.** `engines: node >= 22`، وإحنا على `>= 20.11` في `tools/setup.sh`. رفع الحد
   يكلّف كل مستخدم للاستوديو مقابل مكسب صفري.
6. **طبقة تبعية جديدة على مسار حرج.** Chromium + ffmpeg + ffprobe + ٧٨ حزمة npm عشان نعمل
   اللي K بيعمله بلا اعتماديات إضافية.

## اللي نستفيده فعلًا (بدون تبعية ولا كود منقول)

مرتب بالأولوية، وكله تنفيذ أصلي في `tools/reel_lint.py` أو `space3d`:

| # | الفكرة | الوضع عندنا | التنفيذ المقترح |
|---|---|---|---|
| ١ | **فحص تباين WCAG AA للنصوص** على البالِت (١٤/١٤ عندهم) | **ناقص تمامًا** — `visual_direction.py` بيربط كلمة بمعالجة بس مش بيقيس تباين | دالة أصلية: نسبة التباين لكل `(text token, background token)` من `brand.json` بقاعدة ٤.٥:١ / ٣:١ للنص الكبير، وترميه `T06` |
| ٢ | **`first_frame_empty`**: الفريم صفر ما يكونش خلفية فاضية — هو الـthumbnail | ناقص — `S02` بيتحقق إن أول مشهد يبدأ عند ٠ بس مش إن فيه محتوى | قاعدة `S06`: أول مشهد لازم يكون فيه عنصر مرئي عند `t = 0` |
| ٣ | **٧ بلوكات 3D** (`cuboid-carousel`, `orbit-card`, `frost-sequence-camera-orbit`, `glass-shard-title`, `canopy-part-title`, `wireframe-portal-title`, `code-slice-hero`) | `space3d` عنده box/prism/camera/shade بس | مرجع بصري لما نضيفه لاحقًا (cylinder/torus/explode) — نقل **سلوك**، مش كود |
| ٤ | **`audio --read`**: تقسيم التسجيل لسطور voice/effect/music + onsets + silence في زمن الفيلم | عندنا `vo_length.py` (سكتات وحدود مشاهد) و`sfx.py` بس مفيش تصنيف | فكرة لتوسيع `vo_length` لو احتجنا downbeats/sections |
| ٥ | **قواعد caption للـlint** (`hard kill` بعد خروج الكابشن، `fittext scale mismatch`) | عندنا `caption_motion.py` حتمي، فالمشكلة مش موجودة بنفس الشكل | لا شيء — الفكرة مطبقة بالفعل |

## لو احتجنا HTML→فيديو يومًا (مسار تجريبي، مش افتراضي)

يثبت إنه شغال هنا بالوصفة دي، ومحكوم بثلاث شروط:

```bash
npm i hyperframes@0.9.9 --ignore-scripts          # Node >= 22
export HYPERFRAMES_BROWSER_PATH=$(node tools/chromium.mjs --path)
export LD_LIBRARY_PATH=$(node -e "..." )          # نفس سكربت tools/chromium.mjs --env
export HYPERFRAMES_FFMPEG_PATH=… HYPERFRAMES_FFPROBE_PATH=…   # ffprobe لازم ثنائي حقيقي
# ونسخ gsap.min.js والخطوط داخل المشروع — الـCDN مسدود
npx hyperframes render -o out.mp4 --workers 1
```

**متى يُسمح به:** مشهد واحد معزول طلبه المستخدم صراحةً بواجهة HTML، وجميع أصوله محلية،
وبالِت من `brand.json`. **مش** مسارًا رابعًا للمحركات ولا استبدالًا لـK.

## القرار

**لا نتبنّى HyperFrames كمحرك ولا كتبعية.** نأخذ منه فكرتين قابلتين للقياس الآن (تباين WCAG،
والفريم الأول غير الفاضي) وتصورات لـ`space3d`. أي مساس بحرّاس الهوية أو التوقيت أو العربي
يُرفض، وأي استخدام مستقبلي يبقى مسارًا تجريبيًا معزولًا بخطوات موثّقة أعلاه.

الأثر المرجعي: `cache/hyperframes-ar-poc.png` (٤ فريمات من رندر عربي حقيقي) و`cache/hyperframes-ar-poc.mp4`.
