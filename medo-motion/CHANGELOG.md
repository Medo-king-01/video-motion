# Changelog — Medo Motion (private fork)

## 1.1 — 2026-11-01 — agent-agnostic studio + new contract
- **Works with any coding agent.** The operating contract moved to `AGENTS.md` at the
  repo root; `SKILL.md` now defers to it and no longer assumes Claude Code.
  Added `tools/setup.sh`, `tools/doctor.py`, `tools/new_project.py`.
- **Contract changed to four inputs:** script · scene direction · Medo's VO · Medo poses.
  Everything else (visuals, SFX, music, timing, assets) is produced by the agent.
- **Removed the logo and the series name everywhere.** No chip, no episode number, no
  reserved logo circle in `scenes.py`; `brand.json` (`logo: null`, `logo_rule`),
  `BRAND.md` §1/§6/§10, `TASTE.md`, `medo-playbook.md` §1/§7 updated. End cards are
  typographic only. The ElevenLabs onboarding flow was dropped: VO comes from Medo,
  TTS is opt-in only.
- **New Arabic shaping fallback** `templates/procedural-reels/arabic_shape.py`
  (HarfBuzz shaping + FreeType rasterising) for Pillow builds without libraqm.
  Verified: joins, RTL run ordering, mixed Latin/digits, 25,000 / 12:30, strokes
  composited behind the glyphs, ink-tight sprites so caption layout is unchanged.
- **Engine K rebranded:** `data.js` loads Cairo, `lib/kit.js` FONTS default to Cairo,
  `explainer-example.js` loads Cairo only; `#E8322B` → brand `#E5262B`.
- `lib/brand.js`: background gradients (`bgDarkTop/Bottom`, `bgLightTop/Bottom`),
  `chipY` removed. `brand_check.py --project` now also audits `lib/brand.js`
  (colours, gradients, font, safe zones) and finds `src/lib` copies.
- `preflight.py`: the `medo` block no longer collapses to an error when Pillow is
  missing; it reports `arabic_shaping: raqm | harfbuzz-fallback | NONE`.
- `render.js`: accepts `playwright-core` (works with the bundled Chromium).
- Verified here: engine P 8-frame chunk + 8-frame contact sheet with correct Arabic
  captions; engine K 12 frames through Chromium 153; `brand_check` PASS.

## 1.0 — 2026-11-01 — fork of Khaam Motion 1.4.1
- Added `brand/` (BRAND.md + brand.json), `styles/medo-red-circle.md`, `reference/medo-playbook.md`, `scripts/brand_check.py`, `templates/render/lib/brand.js`; `templates/TASTE.md` pre-filled with locked brand values.
- Added `templates/procedural-reels/` extracted from AGENT_MASTER_BRIEF_v4 and made portable: relative paths, Cairo-first font resolver (variable-font bold), brand-silhouette PLACEHOLDER when Medo poses are missing, `cutout.py` CLI, cross-platform `run_all.py`.
- Encode changed to the brief's MASTER spec (CRF 13, tune animation) — the brief's appendix code still used CRF 17/fast.
- Fixed: chunk files now carry start+end in the name and `run_all.py` deletes stale chunks when code/assets/timings change (the original silently reused them).
- Dialect switched from Gulf to Egyptian. Normalised line endings to LF.
- Tested here (Linux sandbox): 8-frame contact sheet, 45-frame chunk encode (4.9 Mbps), chunk resume + stale invalidation, two-pass loudnorm (−14.5 LUFS, TP −5.1). NOT tested: Windows, real Cairo font, real Medo poses, full 55 s render.

# سجل الإصدارات — «موشن خام»

## 1.4.1 — 2026-10-26 — راشد الحازمي (خام)
- **نطق الاختصارات في الصوت المعلّق** (`reference/voiceover.md`): الاختصارات اللي تنقرى حرف حرف (SEO، GPT) تنكتب بالإنجليزي وبحروف كبيرة في النص اللي يروح لـ ElevenLabs، مثل `Chat GPT`. والكلمات والأسماء الإنجليزية اللي تنقرى ككلمة تنكتب بالعربي مثل ما تنطق (قوقل، كلود كود)، وAI يمشي الاثنين. السبب: «سيو» بالحروف العربية انقرت "Co" بدل SEO. الكابشن على الشاشة ما تغيّر.

## 1.4.0 — 2026-10-26 — راشد الحازمي (خام)
- **المسار السريع: ٣ محطات بس.** (أ) رسالة خطة وحدة: ٣ هوكات، والسكربت، والستايل، وهل فيه صوت معلّق وتكلفته. (ب) لوحة storyboard وحدة. (ج) **أول معاينة توصلك كاملة**: حركة ومؤثرات وصوت معلّق مع بعض. بعدها النسخة النهائية بدقة كاملة.
- **ما فيه جولات زيادة:** لا معاينة صامتة، ولا جولة للصوت لحاله، ولا معاينة منفصلة لأول ٣ ثواني. الصوت يتولّد ويتركّب مع الحركة في نفس المرة، والفحوصات الداخلية (القياس والتزامن والعلو) يسويها Claude بنفسه بدون ما يعرضها عليك.
- **يتعلم ويتذكر:** الفيديو الجديد في نفس المجلد ياخذ ستايل آخر مشروع ويسأل سطر واحد: «نفس الستايل؟». وأي تفضيل عام تقوله ينحفظ في `~/.cache/khaam-motion/user-taste.md`، ويطبقه في كل المشاريع بعدها. والمستخدم الراجع ما يمر بالتعريف من جديد.
- `preflight.py` يقول هل ملف التفضيلات موجود.

## 1.3.0 — 2026-10-26 — راشد الحازمي (خام)
- **الهوك أولاً** (`reference/hooks.md`): قبل أي حركة، Claude يبحث عن هوكات مجالك (إذا عنده بحث في الإنترنت)، ويكتب ٣ خيارات (الجملة المنطوقة، والنص على الشاشة، وحركة أول ٣ ثواني)، وتختار واحد، ويبني أول ٣ ثواني ويعرضها عليك قبل الباقي. فيه ١٢ عائلة هوكات بقوالب عربية، وقواعد حركة أول ٣ ثواني.
- **إصلاح:** أداة الرندر والمعاينة صارت تفهم `~` و`%USERPROFILE%` و`$HOME` في ملف الإعدادات، مثل سكربتات Python. (اكتشفه Claude أثناء تجربة المهارة على مشروع حقيقي.) واسم `ffmpeg` بدون مسار صار يشتغل بعد.
- **اللغة:** نصائح نهاية التعريف الأول تطلع بلغة المستخدم بس (بدون عناوين إنجليزية).

## 1.2.0 — 2026-10-26 — راشد الحازمي (خام)
- **عرض الصوت المعلّق:** وقت التثبيت وأول مشروع، Claude يشرح الصوت بالذكاء الاصطناعي (ElevenLabs، نموذج Eleven v4): وش يضيف، وكيف تسوي مفتاح API وتربطه بأمان، والفرق بين الخطة المجانية والتجارية، وإنه يستأذن قبل كل طلب مدفوع. وإذا ما تبيه، يكمل موشن مع مؤثرات مجانية.
- **ما يتكرر:** الاختيار ينحفظ في `~/.cache/khaam-motion/onboarding.json`. المشاريع اللي بعدها تسأل سطر واحد بس في البداية: «تبي صوت معلّق ولا موشن بس؟».
- `preflight.py` صار يقول هل مفتاح ElevenLabs موجود (بدون ما يطبع قيمته)، وهل التعريف الأول انعمل.

## 1.1.0 — 2026-10-26 — راشد الحازمي (خام)
- **نظام ريلز الشرح** (`reference/explainer-reel-system.md`): طريقة إخراج كاملة لريلز الشرح والأدوات والقوائم، مستخلصة من تحليل ريلز ناجحة: هيكل السكربت (هوك برقم، ليش الحين، دليل، قائمة، «علّق الكلمة»)، والإطار الثابت (تسمية القسم، والتقدّم، والحساب)، ونظامين للكابشن (تحريري فوق، أو أزرار كيبورد تحت)، وقاعدة «لكل جملة صورة حرفية»، وانتقالات نقاط الطباعة أو العوالم اللونية، وخاتمة التعليق ثم الرسالة.
- **عُدّة العناصر** (`templates/render/lib/kit.js`): جوال، ونافذة برنامج وتيرمنال، وقائمة مهام، وبطاقة، ومجلد، وختم، وشارة، وعدّاد يدور، وشريط مقابس للتقدّم، ودائرة تحديد، وخطوط انفجار، ومسح بنقاط الطباعة، ونقاط طباعة للصور، وورق بحبيبات، ونهاية «علّق ← وصلتك الرسالة». كلها تحترم قواعد العربي.
- **مثال كامل بالعربي:** `templates/render/scenes/explainer-example.js` (11.5 ثانية).
- **الستايلات صارت أمثلة للإلهام:** ستايل المستخدم أولاً، وClaude يبنيه من مراجعه ويحفظه في مشروعه. شلنا 3 ستايلات خاصة بعلامتنا، وأضفنا مثال «الشرح التحريري».
- الفحص: معاينة contact sheet، وصور ثابتة، وMP4 كامل 1080×1920 مع مؤثرات CC0 من Openverse. انصلحت ملاحظتين: الصفر الهندي «٠» يشبه النقطة في التسميات (صارت 01)، ومسافة تعليق الخاتمة.

## 1.0.0 — 2026-10-26 — راشد الحازمي (خام)
أول إصدار عام.

- **ابدأ هنا:** تشغيل أول بالعربي. Claude يعرف هل أنت في تطبيق Claude أو Claude Code، ويوجهك للتثبيت والرفع (Customize ← Skills)، ويوصيك بـ Opus 5.5 مع effort ‏max، ويشرح كيف تضيف أشياءك بأمان.
- **طبقة العربي:** قواعد الكتابة العربية في الموشن (ما نكسّر الحروف، اتجاه RTL، الحركة بالكلمة أو بالقناع، الأرقام، والنصوص المختلطة) + مساعد `templates/render/lib/arabic.js` + مشهد عربي تجريبي.
- **فهرس الخطوط العربية:** خطوط مجانية (OFL) مع وصفها واستعمالها، وخطوط تجارية مع مصدرها. سكربت `scripts/get_fonts.py` ينزّل المجانية مع رخصتها.
- **مكتبة الستايلات:** 10 ستايلات جاهزة بالألوان والخطوط والحركة والصوت.
- **صوت مجاني:** `scripts/openverse_sfx.py` يبحث وينزّل مؤثرات من Openverse بفلتر الاستخدام التجاري، ويكتب ملف النسب تلقائياً.
- **الصوت المعلّق:** دليل Eleven v4 كامل، وسكربت `scripts/gen_tts_elevenlabs.py` (توليد، واستنساخ صوت بموافقة، وحوار).
- **storyboard قبل الرندر:** إطارات ثابتة للموافقة قبل الفيديو الكامل.
- الاسم «موشن خام»، ورخصة «خام»، ومتغيرات البيئة `KHAAM_*`، وإعداد المشروع في `.khaam/config.json`.

### الفحوصات اللي انعملت لهذا الإصدار (2026-10-26، Windows 11، Python 3.11، Node + Playwright Chromium)
- كل سكربتات Python تترجم (`py_compile`)، و`preflight.py` يشتغل ويقرأ إعداد `.khaam/config.json`.
- السكربتات الموجودة تشتغل بعد تغيير الأسماء: خطة الصوت المعلّق، وخطة المؤثرات، وفحص المكتبة، وخطة نماذج الصوت، وجرد الصوت.
- `get_fonts.py --check`: الـ 41 خط كلها موجودة في مستودع Google Fonts الرسمي برخصة OFL. تنزيل 3 خطوط مع الرخصة وملف المصدر وتسجيلها في `manifest.json`.
- عيّنة الخطوط: الـ 33 خط عربي رُندرت في Chromium وكلها أظهرت العربي صحيح (`reference/arabic-fonts-specimen.jpg`).
- `openverse_sfx.py`: بحث ببدون مفتاح، وتنزيل صوت CC0 وصوت CC BY. سطر النسب انكتب للـ CC BY بس، والسكربت رفض الكتابة فوق ملف موجود.
- الرندر: المشهد العربي (كلمات كاملة، كشف من اليمين لليسار، شريط يمشي من اليمين) بخط Kufam، معاينة contact sheet، وMP4 كامل 1080×1920 مع صوت. الحروف متصلة، والشدة والنقاط سليمة.
- ما انجرّب: رفع المهارة في تطبيق Claude (Customize ← Skills)، وmacOS وLinux، وطلبات ElevenLabs المدفوعة، وجلسة مبتدئ كاملة من الصفر.
