# مهارة Remotion لمحرك R — تقرير التكييف والتحقق

**التاريخ:** 2026-11-09 · **النطاق:** تدقيق حزمة المهارات الرسمية `remotion-dev/skills` (v4.0.541) ودمجها داخل الاستوديو **كتكييف أصلي** لا كحزم مستوردة؛ التحقق من كل ادعاء من الكود والمانيفستات؛ بلا تشغيل رندر فعلي، وبلا نسخ أي ملف من upstream.

## القرار

المهارة اندمجت كملحق اختياري في `medo-motion/skills/remotion/SKILL.md` — **من غير أي تعديل** على المهارة الأساسية `medo-motion/SKILL.md` أو المحركات أو الـtemplates أو CI بخلاف خطوة تشغيل اختبار الحراسة. الغرض: مرجع واحد يعرف الوكيل فيه إمتى وإزاي يستعين بإرشادات Remotion الرسمية وهو شغال على محرك R، وفي المقابل إيه اللي **لا** ينطبق على عقد استوديو ميدو. حراسة الانجراف في `tests/test_remotion_skill.py`.

## المصدر والتدقيق

| البند | القيمة |
|---|---|
| المستودع | `github.com/remotion-dev/skills` |
| الإصدار | `4.0.541` (frontmatter في كل مهارة) |
| الالتزام المدقوق | `a2824c6` (pushed 2026-11-05) |
| تاريخ التدقيق | 2026-11-09 |
| المحتوى | 13 مهارة على المستوى الأعلى (+ مجلد `remotion-best-practices/` يحتوي نسخًا مدمجة من البقية، ومسارات `remotion-maps/techniques/*` لأماكن الجغرافيا) |
| الترخيص في upstream | **لا يوجد ملف ترخيص ولا حقل `license`** في مستودع skills (`gh api repos/remotion-dev/skills` → `license: null`). Remotion نفسه تحت **Remotion License** مخصّصة (`remotion-dev/remotion` → NOASSERTION / "Other") |

**نتيجة الترخيص:** لا يوجد ما يجيز إعادة توزيع upstream حرفيًا. لذلك لم يُنسخ أي ملف؛ المهارة الجديدة كتابة أصلية تلخص المعرفة التقنية وتوجّه للقرارات، مع الإسناد في الملحق وهنا. أي تركيب مستقبلي لـ`npx skills add` داخل هذا المستودع ممنوع — هو بالضبط ما اختصره هذا الدمج بشكل محكوم.

## حالة المهارات الـ13 والقرار لكل واحدة

| # | المهارة | القرار | السبب باختصار |
|---|---|---|---|
| 1 | `remotion-best-practices` (router) | **متكيف** | التنظيم العام والمعاينة قبل البناء والرندر عند الطلب الصريح فقط — كلها متوافقة مع الاستوديو ومُضمَّنة في §5/§2 |
| 2 | `remotion-create` | **متكيف** | الـscaffold الرسمي (`create-video`) يتعارض مع `tools/new_project.py --engine r` (حزم مثبتة + بوابات النص/الخطة). حدود video-layout (النص المهم ≥ 80px من الجوانب، ~84px للعنوان الرئيسي عند 1080) محفوظة كإرشاد تقريبي تحت قاعدة الهوية |
| 3 | `remotion-markup` | **متكيف** | القواعد الجوهرية (إطار = الساعة، `interpolate` inline، clamp، `scale`/`translate`/`rotate` بدل `transform`) متوافقة ومُضمَّنة §5؛ `arabic-text.md` متوافق مع `arabic-typography.md` — قواعد الاستوديو تفوز دائمًا |
| 4 | `remotion-studio` | **متكيف** | `npx remotion studio` يُستبدل بـ`npm run studio` (بوابات `text-direction`/`stage`/`slide-wall`/`one-take` + Chromium المشترك + `--no-open`) |
| 5 | `remotion-render` | **متكيف** | `npm run render -- --audio` بعد بوابة VO المقاسة؛ `npm run stills` للفريمات؛ الشفافية فقط لتسليم overlay صريح — مش لريلز عادي |
| 6 | `remotion-maps` | **مرجع فقط** | Mapbox/MapTiler/Cesium = شبكة + مفاتيح + افتراض 16:9؛ ممنوع في مسار الرندر الافتراضي. الخريطة فقط بموافقة صريحة + أصول مرخّصة مسجلة في `assets/CREDITS.md` (SVG/GeoJSON مرسوم) |
| 7 | `remotion-captions` | **متكيف** | `Caption` type مفهوم كشكل تبادلي؛ الترنسكريبشن المحلي يبقى `tools/whisper_align.py` (بدون GPU/تحميل موديل)؛ التايمينج من `word-timings.json` هو الحاكم؛ SRT المرفوعة مرجع محتوى فقط |
| 8 | `remotion-saas` | **مرجع فقط** | الاستوديو يسلّم MP4، مش تطبيقات. `<Player>`/Lambda/Vercel مسارات لطلب تسليم تفاعلي — موجز مختلف يستلزم موافقة |
| 9 | `remotion-interactivity` | **مرجع فقط — غير متحقق** | `Interactive.*` موثقة في upstream 4.0.541؛ القالب مثبت على **4.0.539** → غير متاحة/غير مختبرة على نسخة الاستوديو. تُفعَّل فقط بعد ترقية مقصودة + `selftest --remotion` + مراجعة |
| 10 | `remotion-multimedia` | **مرجع فقط** | Mediabunny في المتصفح ≠ مسار الاستوديو؛ القياس بـ`tools/ffprobe_shim.py` و`tools/vo_length.py` وffmpeg — بدون شبكة |
| 11 | `remotion-license` | **متكيف** | روابط الترخيص/FAQ/الشروط + remotion.pro أُبقيت كمؤشر؛ ترخيص Remotion مستقل عن ترخيص المستودع وعن OFL؛ يُراجع قبل أي استخدام تجاري/توزيع |
| 12 | `remotion-upgrade` | **متكيف** | الترقية: `npx remotion upgrade` داخل المشروع (أو يدويًا بتوحيد كل `@remotion/*` على نسخة واحدة + محاذاة `mediabunny`/`zod` + الإبقاء على zod override لحد ما Remotion يدعم Zod 4.6.x أصيلًا + `selftest --remotion`). خطوة `npx skills update` من upstream **لا تُستخدم** — لا شيء نسخة في المستودع |
| 13 | `remotion-docs` | **متكيف (معتمدة)** | Algolia + إلحاق `.md` لكل رابط وثائق — مفيد وبدون تثبيت؛ يحتاج شبكة، والتحقق دائمًا من النسخة المثبتة 4.0.539 لا من الذاكرة |

## التعارضات البنيوية وكيف اتحلت

1. **المتصفح أثناء الرندر:** upstream يفترض متصفح Remotion المدمج؛ الاستوديو يستخدم Chromium المشترك من `tools/chromium.mjs` (`docs/remotion.md`). **الحل:** `npm run studio`/`render` فقط؛ `--browser-executable` وإعادة الاستخدام ممنوعان إلا بطلب صريح من المستخدم.
2. **الخطوط:** upstream يوصي بـ`@remotion/google-fonts`؛ الاستوديو رندره offline بلا أي جلب من الشبكة أثناء الرندر، والخطوط OFL محلية (`public/fonts/` متولدة عند الاسكفولد؛ `assets/fonts/fonts.json` هو المانيفست). **الحل:** خطوط محلية فقط.
3. **الصوت/المدة:** upstream يبني VO بـElevenLabs + `calculateMetadata`؛ عقد الاستوديو: التعليق ملك ميدو، المدة من `tools/vo_length.py`، و`calculateMetadata` لا يخترع مدة أبدًا. **الحل:** رفض مسار TTS في أي تسليم.
4. **الحزم:** upstream يستخدم `@remotion/media` و`@remotion/effects` بكثرة؛ القالب لا يبيع إلا remotion core. **الحل:** الإضافة فقط بقرار مقصود (`npx remotion add`) + توحيد النسخ + قيد في CREDITS + `selftest --remotion`.
5. **النسخ:** upstream يصف 4.0.541؛ القالب مثبت 4.0.539 (react 19.3.1، zod override ^4.6.7). **الحل:** كل ادعاء حساس للنسخة معرَّف كـ"غير متحقق" مع مسار تفعيل صريح (§8 في المهارة).
6. **التثبيت نفسه:** `npx skills add/update` يكتب مجلدات خاصة بالوكلاء؛ الاستوديو عام (host-agnostic). **الحل:** لا تثبيت؛ المهارة نفسها هي الدمج المحكوم.

## ما أُنشئ / اتعدل

- `medo-motion/skills/remotion/SKILL.md` — المهارة (ملحق اختياري).
- `tests/test_remotion_skill.py` — 14 حراسة انجراف.
- `docs/remotion-skill.md` — هذا التقرير.
- `docs/README.md` — سطران في الفهرس.
- `.github/workflows/ci.yml` — خطوة تشغيل اختبار الحراسة.
- `assets/CREDITS.md` — سطر إسناد (تكييف لا نسخ).
- `CHANGELOG.md` — قسم Unreleased بتاريخ 2026-11-09.

## الحدود والافتراضات الصريحة

- **لم يُشغّل أي رندر ولا `npm ci`** أثناء الدمج: التحقق ساكن (قراءة الكود والمانيفستات) + اختبارات بايثون. `selftest --remotion` يُشغّل عند أول استخدام فعلي أو أي تغيير في القالب.
- **Interactivity غير مختبرة على 4.0.539** — موثقة كمرجع فقط حتى ترقية مقصودة.
- **لا خرائط / لا TTS / لا ترنسكريبشن GPU** في مسار التسليم — القرار مقصود ومبيّن.
- أرقام المانيفستات (2,239 تقنية، 163 ستايل، 49 وضعية…) **لم تُنسخ** في المهارة عمدًا؛ المانيفست هو المرجع والكيبر جاي من حراسات scene-director، ونسخها هنا كان سيكرر الانجراف المعروف في وثائق قديمة.
- المهارة تُراجَع دوريًا: إعادة تدقيق upstream (`git fetch` على المستودع + مقارنة `skills/*/SKILL.md` مع §4 هنا) ثم تحديث النص والاختبار والتقرير معًا.

## التحقق

- `python3 -m pytest tests/test_remotion_skill.py` → **14/14** (انظر CI).
- لم تتغير أي قدرة تشغيلية؛ `projects/` لا تزال خارج Git؛ لا حزم npm أضيفت؛ لا كود من upstream أُضيف.
