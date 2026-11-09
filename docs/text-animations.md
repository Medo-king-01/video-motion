# text-animations — كتالوج حركات النص للريلز

> ٥١ حركة نص من مرجع ريلز، مترجمة لـ**لغة الحركة الموحّدة** بتاعة الاستوديو (مسارات
> `{t, v, ease}` دالة في الزمن)، فبتشتغل في المحركات التلاتة K/P/R بنفس الشكل بالظبط.
> من غير أي كود طرف تالت: التقنيات نفسها معاد التعبير عنها بأرقام، ومعاد تلوينها للبراند.

## الفكرة

المرجع الأصلي كان CSS `@keyframes` بـ`animation: … infinite` — ده مش قابل للـseek
فريم فريم (الرندر بيطلب أي لحظة `t` لازم تطلع نفس الشكل). فالأداة بتفكّ كل حركة لـ
**مسارات حركة رقمية** (opacity / translateY / translateX / rotate / scale / blur)،
والرندر بيحسبها عند أي `t` عبر `keyframes()` / `timeline()`.

```
reels_text_animations.html  ──(text_animations_import.py)──►  motion/text-animations.json   (الكتالوج الكامل، ٥١)
                                                          └─►  templates/render/lib/caption-styles.js  (مقدمات الكابشن الآمنة)
```

## الكتالوج: `medo-motion/motion/text-animations.json`

كل حركة ليها:

| الحقل | معناه |
|---|---|
| `id` / `name` / `nameAr` / `family` | المعرّف، الاسم الإنجليزي والعربي، والعيلة (reels/trending/kinetic/cyber/cinematic) |
| `split` | `word` (كلمة كلمة) أو `char` (حرف حرف — kinetic) |
| `duration` / `ease` | مدة الدورة الأصلية + المنحنى (اسم من `easings.json` أو bezier خام محفوظ زي ما هو) |
| `captionSafe` | `true` = نص من غير صندوق/خلفية/تدرّج — يصلح كابشن |
| `boxed` | `true` = فيه صندوق/شريط (CTA/lower-third) — **مش** كابشن |
| `gradientText` / `underline` | تدرّج لوني على النص / تسطير |
| `colorRole` | دور لوني دلالي (`paper`/`salmon`/`red`/`ink`) — الرندر بيحوّله لـ`PALETTE`، **مفيش hex في المسارات** |
| `keyframes` | الـkeyframes الأصلية (مرجع أمين بالمصدر) |
| `tracks` | المسارات الرقمية `word.opacity/y/x/rotate/scale/blur` — دي اللي بتترندر |
| `cssOnly` | خصائص CSS مالهاش مقابل رقمي (color/text-shadow/clip-path…) — مرجع بس |
| `entrance` | مقدمة مقتطعة `{enter, tracks}` للحركات الآمنة (٠ ← أول ثبات، متقلّصة لـ≤0.45s) |

**الوحدات:** `x/y/blur` بـ**em** (نسبة لحجم الخط؛ الـpx الأصلي اتحوّل عند `REF_PX=40`)،
`rotate` بالدرجة، `scale` معامل، `opacity` ٠..١. الرندر بيضرب em في حجم الخط.

## إعادة التلوين للبراند (من غير indigo/أصفر)

المسارات **مالهاش لون** — اللون دور دلالي (`colorRole`) الرندر بيحلّه من `PALETTE`:
أحمر `#CB271B` / سالمون `#D97F68` / ورق `#F3F2F1` / حبر `#0A0A0A`. أي أصفر/أزرق في
المرجع اتحوّل لدور دافئ (salmon/red). الكابشن دايمًا **من غير صندوق** (الحركات الـboxed
مستبعدة من أنماط الكابشن). الخط Cairo.

## حركة كل نص ظاهر: `style` مطلوب — قرار الوكيل لكل عنصر

القاعدة مش للكابشن بس. أي نص بيظهر على الشاشة — عنوان، هوك، كلمة مفتاحية، رقم/عدّاد،
CTA، ليبل، أو نص جوه كارت/UI — الوكيل هو اللي بيختار له أفضل ستايل حركة في المشهد.
مفيش style افتراضي. الـrenderer في `templates/render/lib/captions.js` (وP في
`captions.py`، وR في `lib/TextMotion.tsx` و`lib/DirectedText.tsx`) بيرفض يرسم لو
الستايل مش متحدد. الوكيل بيختار لكل مشهد في `plan/text-direction.json` ويبرّر اختياره،
وبيسجّل كل جزء نص ظاهر في `plan/copy.json` بـ`role` (و`id` لو محتاج حركة خاصة):

```bash
python3 tools/text_direction.py projects/<slug> --init   # هيكل من الـbeats
# الوكيل يملأ captionStyle / textStyles / textElements / captionWhy لكل مشهد
python3 tools/text_direction.py projects/<slug> --check  # لازم يعدّي قبل الرندر
```

```json
{ "version": 3, "status": "directed", "decidedBy": "agent",
  "concept": "شرح هادي بيعلى طاقته عند لقطات الإثبات",
  "scenes": [
    { "scene": 1, "captionStyle": "karaoke", "captionWhy": "هوك بيأكد على الكلمة المنطوقة",
      "textStyles": { "title": "zoomPunch", "number": "impact", "cta": "underline", "label": "softFade" },
      "textWhy": "العنوان يدخل بقوة الهوك، الرقم بيخبط، والCTA بيتسطّر",
      "textElements": { "hero-cta": { "role": "cta", "style": "wordPop", "why": "زرّ التعليق لازم يخطف العين في آخر لقطة" } },
      "fontStyles": { "title": { "family": "Alexandria", "weight": 800 }, "number": { "family": "Tajawal", "weight": 800 },
                      "cta": { "family": "Kufam", "weight": 700 }, "label": { "family": "Readex Pro", "weight": 600 } },
      "fontWhy": "عنوان عريض للإمباكت، رقم هندسي واثق، وCTA كوفي مميز",
      "fontElements": { "hero-cta": { "role": "cta", "family": "Rubik", "weight": 900, "why": "الزرّ بخط مدوّر تقيل يبان سوشيال" } } }
  ] }
```

### الخط كمان قرار الوكيل (مفيش Cairo مفروض)

نفس الخطة بتحدد **الخط** لكل نص ظاهر: `fontStyles` لكل دور + `fontElements` لأي عنصر خاص.
الوكيل بيختار الأكثر جاذبية ومناسبة للريل من `assets/fonts/fonts.json` (١٢٥ عيلة، عربي وإنجليزي)،
وبيبرّر اختياره. Cairo/Inter مجرد شبكة أمان لكروم النظام. اللينت **T05** وبوابات الرندر بيرفضوا
أي نص من غير خط مختار، والنص العربي لازم يكون بخط بيدعم العربي. الـhelpers (`drawDirectedText` /
`draw_directed_text` / `DirectedText`) بتطبّق الخط والحركة مع بعض من الخطة.

```js
// كابشن كلمة-كلمة بتوقيت مقاس
import { drawWordCaption, drawDirectedText } from './lib/captions.js';
import { captionStyleFor } from './lib/text-direction.js';
const style = captionStyleFor(direction, scene.index);
drawWordCaption(ctx, t, words, { W, H, style, theme: 'dark' });

// أي نص تاني (عنوان/رقم/CTA/ليبل) — الستايل بيتجاب من الخطة، مفيش default
drawDirectedText(ctx, '٤٢١٠', { direction, scene: 1, role: 'number',
  time: t, start: 0, end: dur, x: W / 2, y: 500, size: 96 });
```

في P استخدم `draw_directed_text(fr, text, direction=..., scene=..., role=..., t=..., start=..., end=..., cx=..., cy=...)`،
وفي R لفّ أي بلوك نص بـ`<DirectedText direction={DIRECTION} scene={i} role="title" time={t} start={0} end={dur}>…</DirectedText>`.
الرسم الخام (`fillText`/`text_sprite`/`txt`) في مشاهد المشروع بيترفض بلينت T04.

`pop` لسه موجود كـ**اختيار صريح** زيّه زي باقي الستايلات (scale 0.94→1 في 0.09s)،
لكنه مش بيفرض نفسه على أي فيديو.

أنماط جاهزة:

| `style` | الشكل |
|---|---|
| `pop` | نبضة سريعة بسيطة (اختيار صريح، مش default) |
| `fadeTilt` / `fadeDrop` / `softFade` / `fadeTiltScale` | دخول بهدوء + ميل/نزول |
| `zoomPunch` / `wordPop` / `impact` / `elastic` | نبض/تكبير/اهتزاز/مطاط |
| `rise` / `drop` / `beat` / `comic` / `hookZoom` | طلوع/سقوط/نبض إيقاعي |
| `karaoke` | **مسح لوني يمين←شمال بالسالمون على مدة الكلمة المقاسة** (من غير صندوق) |
| `underline` | نبضة + خط سالمون بيكبر تحت الكلمة |
| `hormozi` | نبضة Hormozi منزوعة الصندوق (scale+rotate) |

أي `id` من الكتالوج الآمن يشتغل مباشرة كـ`style` (مثلًا `fadetiltblur`، `blurfade`…).
الـaliases موجودة في `STYLE_ALIAS`، والمقدمات المولّدة في `CAPTION_ENTRANCES`.

### دليل الاختيار حسب المود (إرشادي — القرار للوكيل)

| المود / السياق | ستايلات مقترحة |
|---|---|
| شرح وهادي / معلومة | `softFade` · `fadeTilt` · `fadeDrop` |
| هوك وطاقة عالية | `zoomPunch` · `impact` · `wordPop` · `hookZoom` |
| ترند وتوكيد على كلمة | `karaoke` · `underline` · `hormozi` |
| إيقاع ومونتاج سريع | `beat` · `elastic` · `comic` |
| لحظة عاطفية / هدوء | `softFade` · `blurfade` · `rise` |

نوّع بين المشاهد حسب المعنى، مش عشوائي. لو كررت نفس الستايل كـmotif مقصود، اكتب
`motifReason` في الخطة عشان الـlint ما يحذّرش.

## التوقيت المقاس (مش ثابت)

الـstagger والدخول محسوبين من **بداية الكلمة الحقيقية** (`word.start` من
`caption_align.py`)، مش ثابت مصطنع. في `karaoke` المسح بيتم على `word.end - word.start`
(مدة نطق الكلمة فعلاً)، فالكلمة بتتنوّر وهي بتتقال بالظبط — ده أقوى تآزر بين الكتالوج
وخط المحاذاة المقاس. مفيش أي `animation-delay` ثابت.

## التماثل بين المحركات

`tracks` بتتقري بنفس الـAPI في K (`lib/motion.js`) وP (`motion.py`) وR (نسخة motion.js
المتطابقة). الاختبار `tests/test_text_animations.py` بيقارن JS وPython رقميًا على مسارات
الكتالوج (abs=1e-3)، وبيأكد إن كل الأنماط بترسم من غير أخطاء، وإن غياب `style` بيرفض الرسم.

## إعادة التوليد

```bash
python3 tools/text_animations_import.py --html /path/reels_text_animations.html
python3 tools/text_animations_import.py --html /path/... --check   # يتأكد إن المخرجات متزامنة
```

> ملف الـHTML المرجعي **مش** متتبع في git (ملك لطرف تالت) — بيتحط مؤقتًا وقت الاستيراد بس.
> اللي بيتشحن: الكتالوج الرقمي + مولّد الأنماط + الـrenderer، كلهم من تأليف الاستوديو.

## خارج النطاق (المرحلة دي)

- معرض المعاينة الأوفلاين (الخطوة ٦) — لسه.
- الحركات الـboxed (CTA/sticker/lower-third) — للبطاقات والـCTA، مش كابشن.
- تأثيرات `cssOnly` البحتة (glitch/gradient/typewriter/spotlight) — متسجّلة كمرجع في
  الكتالوج من غير مسارات رقمية، ومحتاجه معالجة خاصة لو اتطلب.
