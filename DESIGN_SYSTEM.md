# DESIGN_SYSTEM.md — نظام تصميم استوديو Video Motion

> المرجع الرسمي الموحّد للاستوديو. بيجمع شتات الهوية والخطوط والحركة والمكونات في مكان واحد،
> لكنه **مش بديل** لمصادر الحقيقة الرقمية. لو حصل تعارض: `brand/brand.json` هو المصدر للأرقام
> المقفولة، و`plan/text-direction.json` هو مصدر الاختيارات الإبداعية لكل مشروع، وهذا الملف هو
> الفهرس والقواعد العامة. اقرأه بعد `AGENTS.md` وقبل التخطيط أو الرندر.

## 1) النطاق: إيه هو النظام ده؟

ده **Design System للريلز العمودي والموشن جرافيك** (1080×1920 @30fps)، مش UI Design System
كامل لتطبيق أو موقع. بيغطي:

- الهوية البصرية: البالِتة، الخلفيات، التباين، مناطق الأمان.
- التايبوغرافي: الخطوط المسموحة، اختيار الوكيل، التشكيل العربي.
- لغة الحركة: المنحنيات، الانتقالات، حركات النص، الإيقاع.
- المكونات القابلة لإعادة الاستخدام في محركات P/K/R.
- ذاكرة التصميم لكل مشروع: `TASTE.md` / `STYLE.md` / `plan/design.html`.
- الفرض: لينت، بوابات رندر، اختبارات، ومراجعة بصرية.

## 2) مصادر الحقيقة وترتيب الأولوية

| الطبقة | الملف | دوره |
|---|---|---|
| هوية مقفولة | `medo-motion/brand/brand.json` | الأرقام الملزمة: ألوان، خلفيات، تباين، canvas، safe zones، أحجام دنيا، صوت، تصدير |
| هوية للبني آدم | `medo-motion/brand/BRAND.md` | شرح الهوية والقواعد والتوقيعات البصرية |
| مرايا الهوية | `brand.css` · `templates/render/lib/brand.js` · `templates/remotion/src/brand.ts` | نفس التوكنز للمحرك/الويب؛ `brand_check.py` بيكشف الانحراف |
| الخطوط المسموحة | `assets/fonts/fonts.json` | ٢١ عيلة SIL OFL 1.1؛ المصدر الوحيد للخطوط على الشاشة |
| اختيار الخط والحركة | `projects/<slug>/plan/text-direction.json` | قرار الوكيل لكل مشهد/عنصر: `captionStyle`, `textStyles`, `fontStyles`, overrides وتبرير |
| كتالوج الحركة | `medo-motion/motion/easings.json` · `transitions.json` · `text-animations.json` | منحنيات، ١٤ انتقال، ٥١ حركة نص |
| مكتبة الحركات | `assets/techniques.json` + `docs/techniques.md` | ٥٩ حركة قابلة للسحب/الاختيار |
| ذاكرة المشروع | `projects/<slug>/TASTE.md` · `STYLE.md` · `plan/design.html` | التصميم المعتمد للمشروع الحالي؛ لازم يتزامنوا |
| المكونات | `templates/procedural-reels/` · `templates/render/lib/` · `templates/remotion/src/` | helpers ومكونات كل محرك |
| الفرض | `tools/reel_lint.py` · `medo-motion/scripts/brand_check.py` · `tests/` · بوابات الرندر | منع الانحراف قبل التسليم |

**مقفول vs اختيار الوكيل**

- مقفول: البالِتة، الخلفيات، التباين، مناطق الأمان، الأحجام الدنيا، التشكيل العربي كلمة-كلمة،
  الكابشن من غير صندوق، التوقيت المقاس من الصوت، أهداف الصوت والتصدير.
- اختيار الوكيل: الخط الأنسب والأجذب، حركة كل نص ظاهر، التكوين، الستايل، الأصول، الانتقالات،
  والإيقاع داخل قواعد الحرفة. مفيش خط أو حركة نص افتراضية مفروضة.

## 3) التوكنز الأساسية

### الألوان
- البالِتة v2.6: **١٢ لون** + مشتق واحد `ink_shadow`. مفيش أصفر/أخضر/أزرق.
- الخلفيات بتتبدل مشهد/مشهد: غامق `#0A0A0A→#030303`، فاتح `#F3F2F1→#D8D7D5`.
- التباين: جسم ≥4.5، كبير ≥3. ممنوع نص أحمر على غامق؛ استخدم `salmon`.
- التفاصيل والأرقام في `brand.json` و`BRAND.md`؛ CSS في `brand.css`.

### الخطوط
- ٢١ عيلة OFL في `assets/fonts/fonts.json` (١٢ عربي + ٩ لاتيني).
- الوكيل يختار لكل مشهد/عنصر ويسجّل في `text-direction.json` (`fontStyles`/`fontElements`).
- Cairo/Inter **شبكة أمان لكروم النظام فقط**، مش قرار إبداعي مفروض.
- النص العربي لازم بخط بيدعم العربي؛ التشكيل كلمة-كلمة، RTL، من غير letter-spacing.
- يفضّل زوج عربي×لاتيني بنفس الإحساس، وحد أقصى عيلتين في المشهد إلا لسبب متسجّل.
- الشرح والأزواج والإضافة: `docs/fonts.md`.

### التخطيط والأمان
- Canvas: 1080×1920 @30fps.
- المحتوى المهم y≈200–1350؛ الكابشن مركزه y≈1455؛ مفيش حاجة مهمة تحت y≈1500.
- هامش 40px؛ progress bar y≈64 فقط؛ أرضية الشخصية y≈1380–1400.
- أحجام دنيا: label كارت ≥44px، chip ≥40px، أيقونة ≥128px، كابشن ≥58px.

### الحركة
- منحنيات مشتركة في `easings.json`؛ تايملاين واحد بيشتغل في P/K/R.
- ١٤ انتقال في `transitions.json`؛ ٥١ حركة نص في `text-animations.json`.
- شبكة BPM واحدة للقطع والـhits والميكرو-حركة؛ velocity blur من السرعة الحقيقية.
- كل نص ظاهر له حركة صريحة من الخطة؛ الكابشن بتوقيت مقاس، unboxed، كلمة كاملة.

### الصوت (جزء من نظام الاستوديو)
- طول الفيديو = طول التعليق الصوتي.
- Mix: −14.5 ±0.3 LUFS، TP ≤ −1.5 dBTP. SFX ≈0.40× ذروة الصوت.
- التفاصيل في `docs/audio.md` و`brand.json`.

## 4) قاعدة النص الشاملة

أي نص بيظهر على الشاشة — كابشن، عنوان، هوك، كلمة مفتاحية، رقم/عدّاد، CTA، ليبل، نص جوه
كارت/UI — لازم يكون له:

1. إدخال في `plan/copy.json` بـ`role` (و`id` لو محتاج حركة/خط خاص).
2. حركة صريحة في `text-direction.json` (`captionStyle` / `textStyles` / `textElements`).
3. خط صريح في `text-direction.json` (`fontStyles` / `fontElements`).
4. رسم عبر helpers الموجّهة فقط:
   - K: `drawDirectedText` / `drawWordCaption` + `useDirectedFonts`
   - P: `draw_directed_text` / `draw_word_caption`
   - R: `DirectedText` / `TextMotion`

الرسم الخام (`fillText` / `text_sprite` / `txt`) في مشاهد المشروع مرفوض بلينت **T04**.
غياب الحركة/الخط مرفوض بـ **T03/T05** وبوابات الرندر.

## 5) المكونات حسب المحرك

| المحرك | التوكنز | النص الموجّه | مكونات أمثلة | ملاحظات |
|---|---|---|---|---|
| **P** (Pillow/OpenCV) | `lib.py` + `brand.json` | `captions.py`, `text_direction.py` | presenter, cards, devices, SFX | الأقوى للشخصية والشرح؛ التشكيل عبر HarfBuzz/raqm |
| **K** (Canvas/Playwright) | `lib/brand.js` | `lib/captions.js`, `lib/text-direction.js` | `lib/kit.js`: card/phone/appWindow/chip/CTA/counters | أغنى kit جاهز؛ لازم النص يمر بالhelpers |
| **R** (Remotion/React) | `src/brand.ts` | `DirectedText.tsx`, `TextMotion.tsx` | Presenter + مشاهد React | @font-face من المانيفست؛ التغطية أقل من K kit |
| **Hybrid** | مقاطع متتابعة P/K/R | كل محرك بقواعده | `tools/render_hybrid.py` | مش layer compositor؛ كل segment بمحرك واحد |

**مش component library موحّدة بنفس الـAPI عبر المحركات.** فيه helpers ونماذج، لكن التغطية
متفاوتة. أي مكون جديد لازم يتبني على توكنز الهوية والنص الموجّه، ويتاختبار في محركه.

## 6) ذاكرة المشروع والـStyle Board

- `TASTE.md`: ذاكرة المشروع. §3 Visual design system + §4 Motion language + §5 Sound.
  يتحدّث لحظة اعتماد أي قيمة، وبيكون مصدر الاستمرارية بين الجلسات.
- `STYLE.md`: وصفة الستايل للمشروع الحالي، مترجمة لمراجع/إحساس إلى primitives الاستوديو.
- `plan/design.html`: style board مرئي للمستخدم. لازم يحمل نفس قيم TASTE/STYLE.
- `medo-motion/styles/`: أمثلة إلهام قابلة لإعادة الاستخدام، **مش defaults مفروضة**.
- بعد الاعتماد: علّم الستايل `approved style (locked)` في TASTE، وأي تغيير لاحق يتسجّل.

## 7) سير العمل المختصر

1. `tools/new_project.py <slug> --engine p|k|r|hybrid`
2. قياس الصوت → `plan/beats.json`
3. كتابة النص الظاهر → `plan/copy.json` (كل fragment له role)
4. اختيار الحركة والخط لكل نص → `tools/text_direction.py --init` ثم ملء `text-direction.json`
5. مزامنة `TASTE.md` / `STYLE.md` / `plan/design.html`
6. لينت: `tools/reel_lint.py <project> --scan-code`
7. Prototype: 3 stills → contact sheet → أصول → رندر
8. Mix/master → ≥3 جولات QC بصرية → تسليم

## 8) الفرض والاختبارات

- `brand_check.py`: البالِتة والتوكنز والمرايا.
- `reel_lint.py`: الحرفة + النص:
  - T00/T01/T02: وجود خطة الحركة وصحتها والتنوع.
  - T03: كل fragment له role وحركة.
  - T04: مفيش رسم نص خام في المشاهد.
  - T05: كل fragment له خط من المانيفست، والعربي بخط عربي.
- بوابات الرندر في P/K/R بترفض خطة ناقصة.
- `tests/`: تشكيل عربي، براند، خطوط، حركة، لينت، scaffold، selftest.
- `tools/ci.sh` و`tools/selftest.py` هما بوابة الدمج.

## 9) إضافة أو تغيير قاعدة

- **توكنز هوية:** عدّل `brand.json` أولًا، ثم المرايا (CSS/JS/TS) و`BRAND.md`، ثم اختبار.
- **خط جديد:** أضفه في `tools/fonts_install.py` → `fonts_install.py --only` → `docs/fonts.md`
  و`assets/CREDITS.md` → اختبارات التشكيل/الترخيص. ممنوع خط مش OFL أو مش في المانيفست.
- **حركة نص/انتقال:** حدّث الكتالوج/importer والdocs واختبارات التماثل بين المحركات.
- **مكون جديد:** نفّذه في المحرك المستهدف، خلّيه يقرأ الهوية والنص الموجّه، وأضف اختبار/عاينة.
- **قاعدة مشروع:** سجّلها في `TASTE.md` و`STYLE.md` و`design.html` مع بعض.

## 10) حدود معروفة

- النظام مخصص للريلز/الموشن، مش buttons/forms/data-table لتطبيق ويب.
- تغطية المكونات مش متماثلة بالكامل بين P/K/R؛ K عنده kit أغنى من R.
- `design.html` قالب عام؛ لازم يتعبّى من هوية المشروع وقرارات الخط والحركة قبل الاعتماد.
- `medo-motion/reference/source/` و`CHANGELOG.md` أرشيف تاريخي، مش مصدر قواعد حالية.
- أي نص قديم في مرجع تاريخي بيتعارض مع هذا الملف أو `brand.json` بيتجاهل لصالح المصادر الحالية.
