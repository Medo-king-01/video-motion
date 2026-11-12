# B2 — اللوحة (Board): مشهد كبيانات، ومُفسِّر واحد

اللوحة ملف JSON واحد (`motion/boards/*.json`) يصف مشهدًا كاملًا كعناصر على مسرح، ومعه
**مُفسِّر واحد** يحوّله إلى عمليات رسم في زمن معيّن. مفيش كود مشهد، مفيش `if` باسم العميل،
ومفيش قيمة خارج مفردات الاستوديو: الألوان أدوار براند، الأوضاع من `assets/poses/poses.json`،
والحركات من كتالوج B1.

> **الحالة (2026-11-12):** B2 مكتملة كعقد + مُفسِّر + مدقّق + معاينة. **لم يُنفَّذ رندر فيديو
> حقيقي** في هذه البيئة (لا Chromium)، فالتكافؤ الإطاري مع K يأتي في B5. المزوّد بصور
> (`assets.images`) هو ما يرسم `person`/`image`؛ غيابه خطأ صريح لا إطار فارغ.

## 1. الملفات

| الملف | الدور |
|---|---|
| `medo-motion/schema/board.schema.json` | مرجع بنيوي (المفاتيح المعروفة، `$defs` للمشهد/الحركة/العنصر). التوثيق لا الفرض |
| `tools/board_check.py` | **المدقّق الحقيقي**: بنيوي + دلالي، بأكواد `B00–B09`، و`--json` |
| `shared/js/board.js` | **المُفسِّر** (K) + محوّل Canvas: `boardFrame` / `drawBoardFrame` |
| `medo-motion/motion/boards/explainer-sample.json` | لوحة مرجعية: مشهدان، ٧ ثوانٍ، ستة أنواع، كاميرا + بارالاكس |
| `tools/board_preview.mjs` | معاينة ٤ إطارات SVG من نفس `board.js` (ثابتة بايتًا) |
| `tests/test_board.py` | ٢٨ اختبارًا: المدقّق، المُفسِّر، المحوّل، الـCLI، المعاينة، مزامنة الملفات |

`tools/sync_shared_libs.py` ينسخ `shared/js/board.js` إلى
`templates/render/lib/board.js` (K) و`templates/remotion/src/lib/board.js` (R) — والاختبار
يقارن البايتات، فلا تُحرَّر نسخة المحرك يدويًا أبدًا.

## 2. الشكل

```json
{
  "version": 1,
  "stage": { "width": 1080, "height": 1920, "fps": 30 },
  "duration": 7,
  "seed": 1207,
  "scenes": [
    {
      "id": "intro",
      "start": 0,
      "duration": 3.5,
      "background": "paper",
      "camera": { "from": { "scale": 1.0, "x": 0, "y": 0 },
                  "to":   { "scale": 1.06, "x": 0, "y": -40 },
                  "move": "camera-push" },
      "elements": [
        { "id": "title", "kind": "text", "x": 90, "y": 520, "z": 3,
          "text": "لماذا تبرد الشريحة؟", "size": 96, "color": "ink",
          "move": { "move": "pixel-list", "duration": 0.6, "stagger": 0.08 } }
      ]
    }
  ]
}
```

- الزمن **مطلق على مستوى اللوحة**؛ `at` داخل المشهد نسبي إلى `scene.start`.
- ترتيب الرسم هو `z` فقط (تصاعديًا)، لا ترتيب المصفوفة. عند التساوي يفصل `id` لضمان الحتمية.
- `seed` يُسجَّل ولا يُستخدم عشوائيًا: كل الحركات دوال حتمية.
- `camera` اختياري لكل مشهد، وحركته من حركتي الكاميرا المسجّلتين فقط.

## 3. الأنواع الستة (بلا سابع)

| النوع | الحقول الإلزامية بعد `{id,kind,x,y,z}` | ما يرسمه المحوّل |
|---|---|---|
| `text` | `text`, `size` (+`weight`, `color`, `align`, `maxWidth`) | نص مشكَّل سلفًا؛ `maxWidth` يُمرَّر إلى `fillText` |
| `shape` | `shape` (`rect`/`ellipse`/`line`/`arrow`)، `w`, `h` (+`fill`, `stroke`, `strokeWidth`, `radius`) | تعبئة/حدّ مستدير؛ `line`/`arrow` يحتاجان `stroke` |
| `draw` | `points` (نقطتان على الأقل) (+`stroke`, `width`, `closed`) | خط متعدد، ورأس سهم إن طُلب |
| `data` | `values` (١..١٢ رقمًا)، `w`, `h` (+`color`, `gap`) | أعمدة بعدّاد `data-count` |
| `person` | `pose`, `h` (+`w`؛ الافتراضي `0.62×h`) | صورة الوضعية من `assets.images[id]` |
| `image` | `src`, `w`, `h` (+`fit`) | الصورة من `assets.images[id]` |

إضافة نوع سابع قرار مالك، وتحتاج: محوّل رسم، اختبار إطار، سطرًا في هذا الجدول. النوع غير
المعروف **يُرفض** في المدقّق، ويُرمى استثناءً في المُفسِّر — لا يُتجاهل بصمت.

## 4. أكواد الرفض

| الكود | يرفض |
|---|---|
| `B00` | الجذر ليس كائنًا، `version ≠ 1`، `duration ≤ 0`، `stage` ناقص/غير موجب، `scenes` فارغة |
| `B01` | حقل غير معروف على أي مستوى، أو حقل إلزامي ناقص |
| `B02` | `stage.width/height/fps` خارج المدى المعقول |
| `B03` | مشهد بلا `id`، معرّف مكرر، `start/duration` سالبان أو متداخلان، مشهد يتجاوز `duration`، أكثر من ٦٤ عنصرًا |
| `B04` | عنصر بلا أساس، نوع غير معروف، حقل خاص بالنوع ناقص، قيم سالبة/غير منطقية (`gap` خارج 0..0.9، `values` فارغة، `points` أقل من نقطتين) |
| `B05` | حركة عنصر أو كاميرا غير مسجّلة، أو `duration ≤ 0`، أو `at ≥ scene.duration` |
| `B06` | لون ليس دورًا في `brand.json` |
| `B07` | وضعية ليست في `assets/poses/poses.json` |
| `B09` | `image.src` ليس مسارًا نسبيًا آمنًا (لا `..`، لا مطلق، لا محارف غريبة) |

```bash
python3 tools/board_check.py medo-motion/motion/boards/explainer-sample.json
# Valid board: data=1 · draw=1 · image=1 · person=1 · shape=1 · text=2
python3 tools/board_check.py --json        # {scenes, duration, kinds, has_camera}
```

الخروج: `0` صالح · `1` لوحة مرفوضة · `2` ملف غير مقروء.

## 5. المُفسِّر

```js
import { boardFrame, drawBoardFrame } from './board.js';

const frame = boardFrame(board, 1.6);      // زمن مطلق بالثواني
// { time, sceneId, local, camera: {scale,x,y}, ops: [...] }

drawBoardFrame(ctx, frame, { colors, images });
```

- `ops` مرتّبة بـ`z`، وكل عملية تحمل `{id, kind, z, x, y, scale, rotation, alpha, progress}`
  مع حمولة نوعها (`text`, `shape`, `points`, `values`, `pose`, `src` …).
- الحركة تُطبَّق كـ`progress` في `[0,1]` وتُترك للدالة النقية المقابلة؛ المُفسِّر لا يعرف
  تفاصيل الحركة، فإضافة حركة لا تلمس `board.js` إلا بسطر في `ELEMENT_MOVES`.
- الكاميرا تُطبَّق حول **مركز الإطار** (`translate(w/2,h/2); scale(s); translate(-w/2,-h/2)`)،
  لا حول الزاوية.
- `drawBoardFrame` يعمل `save()`/`restore()` لكل عملية، ويعيد عدد ما رسمه. غياب صورة
  `person`/`image`، أو شكل بلا `fill` ولا `stroke`، يرمي استثناءً صريحًا.
- `boardTimes(board, count)` يولّد لحظات المعاينة من `duration` فقط.

## 6. المعاينة

```bash
node tools/board_preview.mjs medo-motion/motion/boards/explainer-sample.json out/board.html
```

أربعة إطارات SVG (بداية/وسط كل مشهد)، بألوان البراند من `brand.json` عبر خريطة أدوار،
وبلا وقت حائط أو عشوائية — تشغيلان متتاليان يعطيان ملفًا واحدًا بايتًا ببايت.

## 7. ما لا تدّعيه B2

- لا رندر فيديو، ولا مزامنة صوت: لوحة B2 صورة متحركة صامتة. الصوت في B5/B6.
- لا تحرير تفاعلي: الـTimeline هو B5؛ هنا تُقرأ اللوحة وتُعايَن فقط.
- لا WebGL/Three.js: كل شيء Canvas 2D.
- R يملك المُفسِّر (بايتًا ببايت) لكن لا محوّل Canvas مثبتًا بعد؛ قدرته `conditional` كما في B1.
- `fit` على `image` مُعلن في العقد ولا يغيّر المحوّل سلوكه بعد (يرسم `drawImage` مباشرة).
- عرض `person` الافتراضي `0.62×h` قرار عرض لا قياس: صورة الوضعية الحقيقية تجيب نسبتها معها في B5.

## 8. الخطوة التالية

**B3 مكتملة** ([`explode.md`](explode.md)): فكّ/تجميع حتمي فوق `machine-kit.js`.
**B4 مكتملة** ([`cut-plan.md`](cut-plan.md)): خطة قطع مقروءة وقابلة للتعديل، بلا تنفيذ.
**B5 مكتملة** ([`timeline.md`](timeline.md)): جلسة تحرير + حفظ بإصدار + إعادة رندر بنفس البكسلات.
**B6 ✅ منفّذ** — [`profiles.md`](profiles.md) و[`subtitles.md`](subtitles.md). اللوحة (`board.json`)
لم تتغيّر: البروفايل كتلة `profile` في المشروع الموحّد، والترجمة ملف نصي جانبي.
