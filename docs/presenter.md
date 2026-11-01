# ميدو — مكتبة الوضعيات (Presenter poses)

## اللي عندنا | What ships
١٤ وضعية، أصلها صور بـخلفية فاتحة اتقصّت وبقت PNG شفاف، كلها بنفس مقاس الجسم وبنفس خط الأرض،
فالقطع بين وضعية ووضعية مش بيرجّع ميدو لفوق أو لتحت.

| الملف | الوضعية | إنجليزي | الاستخدام |
|---|---|---|---|
| `neutral` | طبيعي | neutral | وضعية الأساس (idle) |
| `explain` | شرح أو تفكير | explaining | وهو بيشرح فكرة |
| `point` | بيشاور | pointing | بيربط كلامه بعنصر على الشاشة |
| `welcome` | الترحيب بالجمهور | welcome | افتتاحية/ترحيب |
| `wave` | التلويح باليد | wave | تحية سريعة |
| `clap` | التسقيف | clapping | تقدير/نجاح |
| `like` | الاعجاب | delighted | إعجاب بحاجة حلوة |
| `thinking` | التفكير | thinking | وقفة تفكير |
| `thinking-deep` | التفكير العميق | thinking-deep | تأمل أطول (قاعد) |
| `puzzled` | الحيرة | puzzled | سؤال/التباس |
| `sad` | حزين | sad | لحظة هبوط |
| `shocked` | مصدوم | shocked | impact cut |
| `walk` | المشي | walking | انتقال حركي |
| `run` | الجري | running | إلحاح/سرعة |

المصدر: `assets/poses/raw/*.jpg` (الأصل زي ما وصل) → المخرَج: `assets/poses/<slug>.png` +
`assets/poses/poses.json`. **متعملش تعديل يدوي على الـPNG** — عدّل الأصل و`make poses`.

## البناء | Build
```bash
python3 tools/presenter_build.py                 # كل الوضعيات + المانيفست
python3 tools/presenter_build.py --only wave,run  # واحدة أو اتنين
make poses                                       # + شيت مراجعة على الخلفية الغامقة
```
الخطوات: إزالة الخلفية (أبيض الاستوديو + الظل الرمادي) → ملء الفتحات الداخلية للجسم (القميص) مع
تفريغ الفتحات اللي الخلفية باينة منها (بين رجلين الكرسي مثلًا) → تقليم → تطبيع الطول إلى **1200px**
مع خطوة 8px → حفظ. المانيفست فيه لكل وضعية: `ar`, `en`, `tags`, `facing`, `scale`, `w`, `h`, `feet`.

> **قاعدة الفتحات:** أي فتحة داخل السيلويت لونها أبيض نقي (mean ≥ 250.5، std ≤ 4) = خلفية → تتفك.
> أي فتحة فيها تظليل (القميص الأبيض mean ≈ 242) = جزء من الجسم → تتحقن. الاختبارات بتغطي الحالتين.

## الاستخدام | Usage
```js
// engine K
import { loadPoses, PoseTrack } from '../lib/presenter.js';
await loadPoses('/assets/poses/');                  // init()
const act = new PoseTrack([{t: 0, pose: 'neutral'}, {t: 1.5, pose: 'explain'}]);
act.draw(ctx, t, { height: 0.62, x: 0.5 });         // feet land on the ground line (1390)
```
```python
# engine P
from presenter import PoseTrack
act = PoseTrack([{"t": 0, "pose": "neutral"}, {"t": 1.5, "pose": "explain"}])
act.draw(fr, t, height=0.62, x=0.5)
```
- `height` نسبة من 1920 (0.62 = 1190px)، و`ground` افتراضيًا 1390 (خط الأرض في البراند).
- `PoseTrack` بيعمل cross-fade **مشكّل** (القديم بيخرج في ٦٠٪ والجديد بيبدأ عند ٤٠٪) بمدة 0.12s —
  التغيير بيبان كـbeat cut مش كـdissolve باهت.
- `medo_wave` / `medo_think` / `medo_point` (الأسماء القديمة) بتتحوّل تلقائي للوضعيات الجديدة،
  فالمشاهد القديمة بقت بتستخدم الصور الحقيقية بدل الـplaceholder.

## الحياة الخفيفة | Idle life
بدون حركة، الصورة المقطوعة بتبان «ميتة». المحركين بيضيفوا نفس الأرقام (اختبار بيقارنهم):

| الحركة | المعادلة |
|---|---|
| تنفّس | `1 + 0.008·sin(2π·0.28·t)` |
| طلوع/نزول | `2.5·sin(2π·0.22·t)` px |
| ميل جانبي | `2·sin(2π·0.13·t + 0.7)` px |
| ميلان الوضعية | `wave` 1.1° @1.05Hz · `clap` 0.6° @2.2Hz · `run/walk` 1.4° @1.6Hz · `shocked` نبضة سريعة |
| نبض إضافي | `run` 7px @1.6Hz · `walk` 3.5px · `shocked` ضربة واحدة عند كل ثانية |

## المشروع | New projects
`python3 tools/new_project.py <slug>` بينسخ `assets/poses/` كامل + `poses.json` جوه المشروع، فالمحركين
بيلاقوه على `/assets/poses/` بدون أي إعداد.

## إضافة وضعية | Adding a pose
1. حطّ الأصل في `assets/poses/raw/<slug>.jpg` (خلفية فاتحة، الجسم كامل في الفريم).
2. ضيف سطر في `POSES` جوّه `tools/presenter_build.py` (العربي/الإنجليزي/التاجات/الميل).
3. `make poses` → شوف الشيت → لو محتاج تدوير/مقاس مختلف حط `scale` في السطر.
4. `python3 -m pytest tests/test_presenter.py` — بيتأكد إن القص نظيف ومفيش هالة بيضا.
