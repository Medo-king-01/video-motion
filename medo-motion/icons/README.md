# طبقة الأيقونات المتحركة — Animated icon layer

> **٢٧٥ أيقونة** جاهزة: ١٢ أيقونة بيت مكتوبة هنا بأسماء عربية، + **٢٦٣ أيقونة من itshover** (كل اللي في
> https://itshover.com/icons) متاخدة من مستودعهم المفتوح (Apache-2.0) ومولّد منها نسخة للمحركين.
> نفس الأيقونة موجودة بصيغة **SVG متحركة** (للويب)، و**Canvas** (المحرك K)، و**Pillow** (المحرك P).
> الألوان مش متخزنة في الأيقونة: بتتمرر وقت الرسم من بالِت البراند (12 لون) → مستحيل أيقونة تخرج برة الهوية.

## الملفات | Files
| الملف | إيه ده |
|---|---|
| `registry.json` | **مجموعة البيت** (١٢): id، اسم عربي، group، شكل، وتوقيت الأنيميشن — دي اللي بتتعدّل بإيدك |
| `itshover/` | نسخة itshover كاملة: `tsx/` (المكوّنات الأصلية ٢٦٣) · `LICENSE` (Apache-2.0) · `registry.json` (مولّد) · `upstream-registry.json` |
| `build.py` | يولّد كل الملفات التانية. `python medo-motion/icons/build.py` · يتحقق: `--check` |
| `svg/<id>.svg` | أيقونة SVG متحركة (CSS: `draw` + نبض النقطة)، stroke = `currentColor`، النقطة = `var(--icon-accent)` |
| `icon.css` | كلاسات `.reel-icon` + المقاسات + سطح فاتح/غامق + `prefers-reduced-motion` |
| `manifest.json` | فهرس مسطّح (للدوكس والتيستات) |
| `examples/PlugConnectedIcon.jsx` | مثال مكوّن React بنفس أسلوب itshover (motion/react) بنفس المسارات |
| `components.json` | تَمبلت إعداد shadcn للبروجكت الويب اللي هتضيف فيه مكونات itshover |

المولَّد بره الفولدر ده (متعدّلهمش بإيدك):
- `medo-motion/templates/render/lib/icons.js` → `drawIcon(ctx, name, t, {...})` للمحرك K
- `medo-motion/templates/procedural-reels/icons.py` → `draw_icon(fr, name, t, x, y, ...)` للمحرك P

## الأيقونات | Icons (12)
`cpu` المعالج · `ram` الرامات · `ssd` التخزين · `display` الشاشة · `gpu` كارت الشاشة · `battery` البطارية ·
`plug-connected` متصل · `wifi` واي فاي · `check-circle` تم · `alert-triangle` تحذير · `arrow-right` التالي · `sparkle` جديد

## الاستخدام | Usage

**المحرك K (Canvas)**
```js
import { drawIcon } from './lib/icons.js';
import { BRAND } from './lib/brand.js';
drawIcon(ctx, 'cpu', t - 0.4, {            // t = ثواني من بداية الأيقونة
  x: 540, y: 900, size: 128,
  color: BRAND.colors.paper,               // على الغامق؛ استخدم ink على الفاتح
  accent: BRAND.colors.salmon,             // على الغامق؛ red على الفاتح
  loop: false,                             // true = تعيد نفسها
});
```

**المحرك P (Pillow/numpy)**
```python
from icons import draw_icon
draw_icon(fr, 'battery', t - 0.4, 540, 900, size=128, color=WHITE, accent=SALMON)
```

**المحرك اللي بره الفيديو (ويب/React)**
```html
<!-- inline الـ SVG، بعدين: -->
<span class="reel-icon reel-icon--on-dark reel-icon--md"> …svg… </span>
```

**مكوّن itshover زي اللي في اللينك**
```bash
cp medo-motion/icons/components.json <react-app>/components.json
npx shadcn@latest add https://itshover.com/r/plug-connected-icon.json
```
> الأمر ده محتاج إنترنت، ومش شغال من الساندبوكس (itshover.com مش متاح هنا). لما تشغله على جهازك، المكوّن بيتحط في `@/components/ui`، وبعدها إما تستخدمه زي ما هو، أو تنقل مساراته في `registry.json` وتعمل Rebuild عشان يدخل المحركين كمان.

## كل أيقونات itshover | The whole library
- **٢٦٣ أيقونة** اتحوّلت تلقائيًا من مكوّنات itshover الأصلية: `python3 tools/itshover_import.py`
- البحث: `python3 tools/itshover_import.py --list | grep -i plug` — نفس الـid اللي على الموقع (`battery-icon`, `gear-icon` …)
- ترقية أيقونة لمجموعة البيت (مع اسم عربي وتعديل حرّ):
  ```bash
  python3 tools/itshover_import.py --promote battery-icon
  python3 medo-motion/icons/build.py
  ```
- الحركة: itshover بتحرّك كل أيقونة بتسلسل مكتوب بـ`motion` (مش قابل للتشغيل على Canvas/Pillow). عندنا كل الأيقونات
  بتاخد نفس أنيميشن الظهور (رسم تدريجي + نبضة) عشان الريل يبقى متسق ومحمي بالهوية.
- **العلامات التجارية:** ٤١ أيقونة براند (Google/Apple/Notion/OpenAI…) معلّمة `group: "brand"` — ممنوع استخدامها
  كهوية أو من غير موافقة ميدو.

## إضافة أيقونة | Add an icon
1. ضيف عنصر في `registry.json` بالـ primitives: `path` (SVG d كامل) · `line` · `poly` · `rect` · `circle` · `ellipse` · `arc` · `dot` · `fillrect` (`fill: true` لأي شكل معبّى).
2. `python medo-motion/icons/build.py`
3. شوفها: `python3 tools/icons_sheet.py` (المحرك P) و `node tools/icons_preview.mjs` (المحرك K).
4. لو لونها/حركتها غلط، عدّل `registry.json` بس — مفيش توليد يدوي.

## قواعد | Rules
- مسموح 12 لون بس (وسايب `ink_shadow` المشتق) — الأيقونة تاخد لونها من البالِت.
- **ممنوع stroke أحمر على خلفية غامقة** (تباين 2.01:1) → على الغامق: stroke = `paper` والأكسنت = `salmon`.
- أقل مقاس أيقونة على الريل: **128px**؛ الخط 2 على شبكة 24 (بيتحجّم مع الحجم).
- أي أيقونة من مصدر خارجي: راجع ترخيصها قبل ما تحطها في `registry.json`. الـ itshover بيوزع مكوناته كـ registry؛ الترخيص النهائي بيتحدد من اللينك نفسه — لو مش واضح، ارسمها بنفسك (زي الـ 12 اللي هنا).
