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

## أنماط الكابشن: `drawWordCaption(..., { style })`

الـrenderer في `templates/render/lib/captions.js` بياخد `style` اختياري. **الافتراضي
`pop` هو نفس السلوك الأصلي بالظبط** (scale 0.94→1 في 0.09s، من غير صندوق).

```js
import { drawWordCaption } from './lib/captions.js';
// words = [{ text, start, end }] بتوقيتات مقاسة (caption_align)
drawWordCaption(ctx, t, words, { W, H, style: 'karaoke', theme: 'dark' });
```

أنماط جاهزة:

| `style` | الشكل |
|---|---|
| `pop` | الافتراضي — نبضة سريعة بسيطة (brand-safe) |
| `fadeTilt` / `fadeDrop` / `softFade` / `fadeTiltScale` | دخول بهدوء + ميل/نزول |
| `zoomPunch` / `wordPop` / `impact` / `elastic` | نبض/تكبير/اهتزاز/مطاط |
| `rise` / `drop` / `beat` / `comic` / `hookZoom` | طلوع/سقوط/نبض إيقاعي |
| `karaoke` | **مسح لوني يمين←شمال بالسالمون على مدة الكلمة المقاسة** (من غير صندوق) |
| `underline` | نبضة + خط سالمون بيكبر تحت الكلمة |
| `hormozi` | نبضة Hormozi منزوعة الصندوق (scale+rotate) |

أي `id` من الكتالوج الآمن يشتغل مباشرة كـ`style` (مثلًا `fadetiltblur`، `blurfade`…).
الـaliases موجودة في `STYLE_ALIAS`، والمقدمات المولّدة في `CAPTION_ENTRANCES`.

## التوقيت المقاس (مش ثابت)

الـstagger والدخول محسوبين من **بداية الكلمة الحقيقية** (`word.start` من
`caption_align.py`)، مش ثابت مصطنع. في `karaoke` المسح بيتم على `word.end - word.start`
(مدة نطق الكلمة فعلاً)، فالكلمة بتتنوّر وهي بتتقال بالظبط — ده أقوى تآزر بين الكتالوج
وخط المحاذاة المقاس. مفيش أي `animation-delay` ثابت.

## التماثل بين المحركات

`tracks` بتتقري بنفس الـAPI في K (`lib/motion.js`) وP (`motion.py`) وR (نسخة motion.js
المتطابقة). الاختبار `tests/test_text_animations.py` بيقارن JS وPython رقميًا على مسارات
الكتالوج (abs=1e-3)، وبيأكد إن الافتراضي `pop` ما اتغيرش، وإن كل الأنماط بترسم من غير أخطاء.

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
