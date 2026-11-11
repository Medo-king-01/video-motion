# الانتقالات — Transition catalogue

## الفكرة | One geometry, two engines
الانتقال = **دالة في التقدّم**. `layer('wipe', 0.42)` يرجّع الماسك والتحويل في اللحظة دي، ومحركَي
الرندر بيرسموا نفس الحاجة:

- **محرك K** (Canvas): `compositeTransition(ctx, a, b, name, p, W, H)` — بياخد طبقتين جاهزتين.
- **محرك P** (numpy/Pillow): `composite(a, b, name, p)` — بياخد مصفوفتين RGB.

كل الأرقام **مُطبّعة** (x/w بنسبة عرض الفريم، y/h بارتفاعه، نصف قطر الدايرة بنسبة العرض)، عشان نفس
الماسك يطلع متطابق في الاتنين — و`tests/test_transitions.py` بيقارن الـJS والـPython رقم برقم.

لغة التسمية مستوحاة من مجموعة **gl-transitions** (الأسماء بس — مفيش كود منها هنا؛ رخص ملفاتها في [`GL_TRANSITIONS.md`](GL_TRANSITIONS.md)) لكن الحساب هنا **vector/CPU** مش GLSL:
مفيش GPU، مفيش وقت حقيقي، فالفريم بيتصدّر بنفس الشكل كل مرة.

## الكتالوج | 14 transitions (`medo-motion/motion/transitions.json`)
| الاسم | الشكل | الصوت |
|---|---|---|
| `wipe` | كشف من الشمال لليمين | whoosh |
| `wipeUp` | كشف من تحت لفوق | whoosh |
| `diagonal` | سلّم أعمدة (كشف مائل) | swipe |
| `iris` | دايرة بتفتح من المركز (pop) | pop |
| `irisClose` | نفس الدايرة بالمقلوب (الخارج هو الجديد) | whoosh |
| `slide` | المشهد الجديد بيزق القديم | swipe |
| `cover` | الجديد بيغطّي من غير ما يزق | swipe |
| `blinds` | شرائح رأسية من فوق/تحت | tick |
| `checker` | بلاطات بتظهر بتتابع | pop |
| `bands` | شرائط أفقية من الجانبين | whoosh |
| `dissolve` | cross-dissolve ناعم | noise |
| `zoom` | الجديد بيستقر من 1.12× مع fade | whoosh |
| `glitch` | صفوف بترتيب مهشّر + رجفة أفقية | glitch |
| `flash` | وميض ورقي سريع (impact cut) | impact |

كل انتقال له `duration` افتراضي **0.5s** و`ease` من مفردات `motion/easings.json` — يعني تقدر تخلي
الـwipe بـ`expoOut` أو الـchecker بـ`bounceOut` بتعديل سطر واحد.

## الاستخدام | Usage
```js
// engine K
import { compositeTransition, makeLayer } from '../lib/transition.js';
const a = makeLayer(W, H, ctx => sceneA(ctx));
const b = makeLayer(W, H, ctx => sceneB(ctx));
compositeTransition(ctx, a, b, 'wipe', p, W, H);     // p = 0 → a … 1 → b
```
```python
# engine P
from transition import composite
frame = composite(frame_a, frame_b, "wipe", p)
```
قاعدة مهمة في المحرك K: **ارسم المشاهد في طبقات أوف سكرين بأبعاد كاملة** (`makeLayer`) ثم امزجها —
الرسم المباشر على ctx بيخلي الماسك يقص نصف رسمة.

## المعاينة والفحص | Preview + QA
```bash
python3 tools/transitions_sheet.py                        # cache/transitions-sheet.png (شيت مراجعة)
python3 tools/transitions_sheet.py --video cache/transitions.mp4   # كليب ١٢ث بالصوت
python3 tools/transitions_sheet.py --only wipe,iris --p 0.3 --cols 2
```
الكليب بياخد صوته من `transitions.json` → `sfx`، يعني بيوريك الانتقال **وصوته** مع بعض.

## إضافة انتقال | Adding one
1. ضيف في `motion/transitions.json` (kind + ease + sfx + params).
2. طبّق نفس الـkind في `transition.py` **و** `transition.js` (الـkind هو الرياضيات، والاسم مجرد اختيار).
3. `python3 -m pytest tests/test_transitions.py` — بيتأكد إن الجدولين متطابقين والهندسة متطابقة رقميًا.

## قواعد الاستخدام في الريل | Editorial rules
- انتقال واحد لكل تغيير مشهد، ومدة 0.4–0.6s في الريل العمودي (أطول = بطيء، أقصر = مش باين).
- في نفس الفيديو استخدم عائلة واحدة (wipe + diagonal + bands) وسيب `glitch`/`flash` للحظات القوية بس.
- متستخدمش `dissolve` كتير — بيدوّي الصورة وكأنها مش متعمولة.
- الانتقال لازم يكون **تحت** الكلام، مش في مكان كلمة مهمة.
- الـ`sound` بتاع الانتقال يتظبط في cue مستقل عشان تقدر تعلي/توطّي لوحده.
