# طبقة الأيقونات المتحركة — Animated icon layer

> نفس الأيقونة موجودة بصيغة **SVG متحركة** (للويب)، و**Canvas** (المحرك K)، و**Pillow** (المحرك P)، كلها من ملف واحد: `registry.json`.
> الألوان مش متخزنة في الأيقونة: بتتمرر وقت الرسم من بالِت البراند (12 لون). يعني مستحيل أيقونة تخرج برة الهوية.

## الملفات | Files
| الملف | إيه ده |
|---|---|
| `registry.json` | **المصدر الوحيد** — كل أيقونة: id، اسم عربي، group، شكل (primitives على شبكة 24×24)، وتوقيت الأنيميشن |
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

## إضافة أيقونة | Add an icon
1. ضيف عنصر في `registry.json` بالـ primitives: `line` · `poly` · `rect` · `circle` · `arc` · `dot` · `fillrect`.
2. `python medo-motion/icons/build.py`
3. شوفها: `python3 tools/icons_sheet.py` (المحرك P) و `node tools/icons_preview.mjs` (المحرك K).
4. لو لونها/حركتها غلط، عدّل `registry.json` بس — مفيش توليد يدوي.

## قواعد | Rules
- مسموح 12 لون بس (وسايب `ink_shadow` المشتق) — الأيقونة تاخد لونها من البالِت.
- **ممنوع stroke أحمر على خلفية غامقة** (تباين 2.01:1) → على الغامق: stroke = `paper` والأكسنت = `salmon`.
- أقل مقاس أيقونة على الريل: **128px**؛ الخط 2 على شبكة 24 (بيتحجّم مع الحجم).
- أي أيقونة من مصدر خارجي: راجع ترخيصها قبل ما تحطها في `registry.json`. الـ itshover بيوزع مكوناته كـ registry؛ الترخيص النهائي بيتحدد من اللينك نفسه — لو مش واضح، ارسمها بنفسك (زي الـ 12 اللي هنا).
