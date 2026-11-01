# الأيقونات المتحركة — مكتبة itshover كاملة جوه الريلز

## الخلاصة | Short answer
**أيوه، كل أيقونات الموقع (٢٦٣) بقت في المشروع** — واتحوّلت لمحركين الرندر.

الموقع نفسه (`itshover.com`) محجوب عن الساندبوكس، لكن **الكود المصدري بتاعهم على GitHub** (مستودع
`itshover/itshover`، رخصة Apache-2.0). فاللي عملناه:

1. **نسخنا المستودع كامل** في `medo-motion/icons/itshover/tsx/` (٢٦٣ مكوّن + نص الرخصة).
2. **حوّلناهم لشكل المحركات** (`tools/itshover_import.py`): بنقرأ الـ`<svg>` من كل مكوّن (path/rect/circle/
   ellipse/line/polyline/polygon + fill + transform)، ونفكّها geometry جاهزة → `itshover/registry.json`.
3. **المولّد** (`medo-motion/icons/build.py`) بيطلع لكل أيقونة: **SVG متحركة** + **دالة Canvas** للمحرك K +
   **دالة Pillow** للمحرك P، كلها بألوان البالِت وقت الرسم.

النتيجة: **٢٧٥ أيقونة** = ١٢ أيقونة بيت (بأسماء عربية وأشكال مرسومة عندنا) + ٢٦٣ من itshover.

## اللي لسه مختلف عن الموقع | What is intentionally different
| | على الموقع | عندنا |
|---|---|---|
| الحركة | تسلسل مكتوب لكل أيقونة بـ`motion` في المتصفح | أنيميشن ظهور واحد متسق (رسم تدريجي + نبضة) — Canvas وPillow مش بيشغلوا React/Web Animations |
| اللون | `currentColor` + أي لون تختاره | بس البالِت (١٢ لون + `ink_shadow`) — بيتحدد وقت الرسم |
| الشكل الهندسي | مسارات SVG كاملة | نفس المسارات (منحنيات كاملة) — SVG وCanvas بيرسموها زي ما هي، Pillow بيفلطحها بدقة عالية |
| البراند | أيقونات Google/Apple/OpenAI… | موجودة ومعلّمة `group: "brand"` — **ممنوع** استخدامها كهوية أو من غير موافقة ميدو |

## استخدمها | Use

```js
// المحرك K — Canvas
import { drawIcon, ICON_NAMES } from './lib/icons.js';
drawIcon(ctx, 'battery-icon', t - 0.4, { x: 540, y: 780, size: 128,
  color: BRAND.colors.paper, accent: BRAND.colors.salmon });
```

```python
# المحرك P — Pillow
from icons import draw_icon
draw_icon(fr, 'gear-icon', t - 0.4, 540, 780, size=128, color=WHITE, accent=SALMON)
```

```html
<!-- ويب: inline الـSVG + الكلاس -->
<span class="reel-icon reel-icon--on-dark reel-icon--md"> …svg… </span>
```

ID كل أيقونة = نفس اسمه على الموقع: `plug-connected-icon`, `gear-icon`, `battery-icon`, `cloud-2-icon` …

## أوامر | Commands
```bash
python3 tools/itshover_import.py --list | grep -i wifi   # يبحث في المكتبة
python3 tools/itshover_import.py                         # يعيد توليد geometry من نسخة itshover
python3 tools/itshover_import.py --promote battery-icon  # ينقلها لمجموعة البيت (اسم عربي + تعديل حرّ)
python3 medo-motion/icons/build.py                        # يبني SVG + المحركين (make icons)
python3 medo-motion/icons/build.py --check                # يتأكد إن كل حاجة متزامنة (في make ci)
python3 tools/icons_sheet.py --group itshover --limit 24  # شيت مراجعة (المحرك P)
eval "$(node tools/chromium.mjs --env)" && node tools/icons_preview.mjs --limit 24 --cols 8   # المحرك K
```

## البنية | Layout
```
medo-motion/icons/
  registry.json            ← مجموعة البيت (١٢، بأسماء عربية)
  itshover/
    tsx/                   ← ٢٦٣ مكوّن أصلي + LICENSE (Apache-2.0)
    registry.json          ← geometry مولّدة (id، group، أشكال)
    upstream-registry.json ← فهرس itshover الأصلي (كان في الريبو)
  svg/<id>.svg             ← ٢٧٥ ملف SVG متحرك (CSS، currentColor + --icon-accent)
  build.py                 ← المولّد (svg + icons.js + icons.py + manifest)
  icon.css                 ← .reel-icon + المقاسات + الفاتح/الغامق
  components.json          ← إعداد shadcn لو حبيت تجيب المكوّنات نفسها في بروجكت React
  examples/Plugin…jsx      ← مثال مكوّن بأسلوب itshover
```
المولَّد بره الفولدر ده (متعدّلهمش بإيدك):
`templates/render/lib/icons.js` · `templates/procedural-reels/icons.py` · `icons/manifest.json`

## قواعد الاستخدام في الريل | Rules
- **ممنوع stroke أحمر على غامق** (تباين 2.01:1) → على الغامق: `paper` + أكسنت `salmon`.
- أقل مقاس **128px** على 1080×1920؛ أيقونة واحدة لكل فكرة، مش بنك أيقونات.
- الأيقونة تفصيلة مش بطل: البطل لسه الدايرة الحمرا + ميدو + الكابشن.
- أنيميشن الظهور بيبدأ مع الكلمة اللي في الكابشن اللي بتقول اسمها.
- أي أيقونة براند (Google/Apple/Notion…) **بموافقة ميدو بس**، وممنوعة كهوية للاستوديو.

## الرخصة | Licence
itshover بـ**Apache-2.0**: الاستخدام التجاري مسموح، ولازم نحتفظ بالإشعار والترخيص (موجودين في
`medo-motion/icons/itshover/LICENSE`، والتفاصيل في `assets/CREDITS.md`). العلامات التجارية مش جزء من الرخصة.

## حدود معروفة | Known limits
- الأنيميشن المخصص لكل أيقونة على الموقع مش منقول (تسلسلاته JS). اللي عندنا: ظهور متسق + نبضة.
- Pillow بيرسم المنحنيات بتفليح (١٤ نقطة للمنحنى) — دقيق لـ256px، وللحاجات الأكبر استخدم المحرك K.
- أيقونات معبّية (filled) بتترسم بلون الـstroke نفسه، مش بأكسنت، عشان تفضل مقروءة.
