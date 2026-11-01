# الحركة — إيه اللي خدناه من motion.dev وTheatre.js

## الخلاصة | Short answer
**أيوه استفدنا من الاتنين، بس من غير ما نحط مكتباتهم جوه الرندر.** السبب واحد: الريل بيتصدّر
**فريم فريم** (نروح للزمن t → نرسم → نرمّز)، وأي مكتبة بتشتغل real-time على DOM هتكسر حاجتين
مهمين عندنا: **الثبات** (نفس الفريم كل مرة) و**السرعة/الاعتمادية** (١٠٨٠×١٩٢٠ × ٣٠fps × طول الـVO — الطول بيتحدد من الصوت مش رقم ثابت).

فخدنا اللي بينفع فعلًا:

| من | خدنا | سيبنا |
|---|---|---|
| **motion.dev** | أسماء ومنحنيات الـeasing (linear/easeIn/easeOut/circ/back/anticipate) بنفس أرقامها · Springs بـstiffness/damping/mass · فكرة `pathLength` (رسم المسار تدريجي) · `stagger` و`at` للتسلسل | `animate()` نفسها — بتشتغل على عناصر DOM في الزمن الحقيقي |
| **Theatre.js** | **نموذج التأليف**: sheets/objects/tracks/keyframes بمواضع زمنية ومنحنيات bezier · تصدير الـstate كـJSON | الـStudio والـruntime — مش محتاجينهم وقت الرندر |

النتيجة: **لغة حركة واحدة** في المحركين (Canvas + Pillow)، بتتألّف إما بإيدك في JSON، أو من
Theatre.js Studio وتتحوّل بأمر واحد.

## اللي موجود في المشروع | What ships
| الملف | إيه ده |
|---|---|
| `medo-motion/motion/easings.json` | **مصدر المنحنيات**: ١٢ cubic-bezier بأسماء motion.dev + ٥ spring presets + توقيتات البراند |
| `templates/render/lib/motion.js` | المحرك K: `ease` · `spring` · `keyframes` · `timeline` · `stagger` · `reveal` |
| `templates/procedural-reels/motion.py` | المحرك P: نفس الـAPI بالحرف ونفس الأرقام |
| `medo-motion/motion/examples/card-entrance.json` | تايملاين جاهز (spring + back + circ) |
| `tools/motion_studio.html` | استوديو صغير أوفلاين: اكتب/عدّل الـJSON، اسحب المؤشر، شوف الحركة والقيم، نزّل الملف |
| `tools/theatre_import.py` | يقرأ Theatre.js state export → تايملاين المحركين (`--list`, `--offset`, `--sheet`, `--out`) |
| `templates/render/scenes/motion-example.js` | مشهد فعلي (٢٢–٢٥ث) كل حاجة فيه متحركة بالتيملاين |

`tests/test_motion.py` بيفشل لو الجداول في الـJS والـPython اختلفت عن `easings.json`، أو لو النتيجتين
مش متطابقتين رقميًا (JS ↔ Python على نفس التايملاين).

## منحنيات بالمعادلات | Equation easings
الـcubic-bezier مش قادر يعمل elastic ولا bounce، فـ`easings.json` فيه كمان `formulas` (معادلات Penner
زي ما هي في حزمة `easing-functions` المIT). الأسماء منفصلة عن مفردات الـbezier فمفيش تعارض:

| العيلة | الأسماء |
|---|---|
| فيزيائية | `elasticIn/Out/InOut` · `bounceIn/Out/InOut` |
| دقيقة | `quadIn/Out/InOut` · `cubicIn/Out/InOut` · `quartIn/Out/InOut` · `quintIn/Out/InOut` |
| ناعمة | `sineIn/Out/InOut` · `expoIn/Out/InOut` · `smoothstep` · `smootherstep` |

```js
ease('bounceOut', p); ease('elasticOut', p); ease('expoIn', p);   // نفس الأرقام في Python
```
`EASING_NAMES` في المحركين بيطلّع القائمة الكاملة (٣٨ اسم) — والاختبارات بتتأكد إن الاسم في
`transitions.json` أو في تايملاين موجود فعلًا.

## التايملاين والانتقالات | Motion + transitions
الانتقالات بقت جزء من نفس اللغة: `medo-motion/motion/transitions.json` + `lib/transition.js` (K)
و`transition.py` (P) — كل انتقال دالة في التقدّم، ومربوط بصوت من مكتبة المؤثرات.
التفاصيل في `docs/transitions.md`، والصوت في `docs/audio.md`.

## صيغة التايملاين | Timeline format
```json
{
  "duration": 2.4,
  "tracks": {
    "card.y":       [{ "t": 0, "v": 260 }, { "t": 0.75, "v": 0, "ease": "spring" }],
    "card.opacity": [{ "t": 0, "v": 0 },   { "t": 0.3,  "v": 1, "ease": "easeOut" }],
    "card.tint":    [{ "t": 0, "v": [203, 39, 27] }, { "t": 1, "v": [217, 127, 104], "ease": "circOut" }]
  }
}
```
- **`ease` بتاعة الكيفريم بتشكّل المقطع اللي بيوصلها** (زي Theatre).
- `ease` ممكن تكون: اسم (`backOut`) · `[x1,y1,x2,y2]` · `"spring"` · `{ "type": "spring", "stiffness": 170, "damping": 16 }` · أي اسم spring preset (`bouncy`).
- القيم: أرقام، أو مصفوفات ألوان (بتتعمل لها interpolation).
- بره التايملاين: أول قيمة قبل البداية، وآخر قيمة بعد النهاية (clamp) — يعني سكرَب آمن.

```js
import { timeline } from './lib/motion.js';
const tl = timeline(spec);
const v = tl.at(localTime);        // { 'card.y': 0.0, 'card.opacity': 1, … }
```
```python
from motion import timeline
v = timeline(spec).at(local_time)
```

## وصفات motion.dev → كودنا | Recipes
| في motion.dev | عندنا |
|---|---|
| `animate(el, { opacity: [0, 1] }, { duration: .3, ease: 'easeOut' })` | `{ 'card.opacity': [{t:0,v:0},{t:.3,v:1,ease:'easeOut'}] }` |
| `animate(el, { y: 0, x: 0 }, { type: 'spring', stiffness: 220, damping: 22 })` | `{ 'card.y': [{t:0,v:300},{t:.6,v:0,ease:{type:'spring',stiffness:220,damping:22}}] }` |
| `{ pathLength: [0, 1] }` | الأيقونات بتستخدم نفس الفكرة: `drawIcon(ctx, name, t, …)` |
| `stagger(0.06)` | `stagger(i, 0.06)` أو ابدأ كل تايملاين عند `start + i*0.06` |
| `at: 1` في sequence | حرّك مواضع الكيفريمات نفسها (كلها أرقام زمن مطلقة) |
| `ease: [0.34, 1.56, 0.64, 1]` | نفس المصفوفة بالحرف |

## سيناريو Theatre.js | Authoring flow
1. على جهاز فيه إنترنت (مش الساندبوكس): `npm i @theatre/core @theatre/studio` في أي تطبيق ويب صغير.
2. اعمل sheet/object بالخصائص اللي بتحرّكها (y, scale, opacity…)، اظبط كيفريمات في Studio.
3. Project → Export → **State** (أو `studio.createContentOfSaveFile('<projectId>')`) → `state.json`.
4. عندنا:
   ```bash
   python3 tools/theatre_import.py state.json --list           # تشوف الـtracks والـsheets
   python3 tools/theatre_import.py state.json --offset 18.5    # تحوّلها وتبدأ عند ثانية ١٨.٥
   make theatre F=state.json OFFSET=18.5                       # نفس الحاجة من الميك
   ```
   - الـhandles بتتحوّل صح: الـhandle الطالع من الكيفريم + الداخل للكيفريم اللي بعده = `[x1,y1,x2,y2]`.
   - الخصائص الـvector (`{x,y}`) بتتفرّع لمسارات: `Card.position.x` / `Card.position.y`.
   - المدة = طول الـsequence في الـsheet (مضاف عليه الـoffset)، مش آخر كيفريم — يعني الهولد في الآخر محفوظ.
5. الحركة تبقى `timeline(json).at(t)` في المحركين — deterministic، بنفس النتيجة في كل رندر.

## الاستوديو الصغير | The offline studio
```bash
python3 -m http.server 8080          # من جذر الريبو
# افتح: http://localhost:8080/tools/motion_studio.html
```
فيه: محرر JSON، سكرَب، تشغيل، قيم لكل المسارات لحظيًا، وتنزيل الملف. مفيش اعتماد خارجي ولا CDN —
بيستورد `lib/motion.js` مباشرة، فالتجربة اللي بتشوفها هي بالحرف اللي هيتصدّر.

## حدود | Limits
- مش بنشغّل `animate()` أو Theatre runtime وقت الرندر: الاتنين real-time، وإحنا محتاجين seek حتمي لكل فريم.
- أنيميشن الأيقونات المخصص لكل أيقونة في itshover (تسلسلات `motion` في المتصفح) مش منقول؛ بدله ظهور موحّد
  من نفس لغة الحركة دي.
- الـspring بيستخدم حل مغلق (closed-form) مش تكامل رقمي: نفس القيمة في JS وPython ومفيش تراكم خطأ.
- الـ`duration` بتاع الـspring طبيعي (مش مدة الكيفريم): لو المقطع أقصر من `springDuration()` الهبوط بيتقطع
  — `springDuration('bouncy')` بيقولك المدة المناسبة.
