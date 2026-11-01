# ميدو — مكتبة الوضعيات (Presenter poses)

## اللي عندنا | What ships
**٢٤ وضعية** في **مقاسين (framings)**، أصلها صور بخلفية فاتحة اتقصّت وبقت PNG شفاف:

- **`full`** (١٤ + ٦ = ٢٠): الجسم كامل، مطبّع على طول ١٢٠٠px، **القدمين على خط الأرض 1390**.
- **`bust`** (٤): نصف جسم (من الصدر لفوق)، مطبّع على ١١٨٠px، **خط الشعر على الدليل 190**.
  القطع من `full` لـ`bust` بيقرأ كـ**push-in** للكاميرا: نفس الوش في نفس المكان، بس أقرب.

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
| `waiting` | إيدين في الجيوب | waiting | idle تانية |
| `warm` | دفء | warm | جملة صادقة (إيد على الصدر) |
| `phone` | ماسك موبايل | phone | مشاهد التقنية |
| `unfold` | بيفتح ورقة | unfold | بيقدّم سكريبت/فكرة |
| `point-up` | بيشاور لفوق | point-up | تأكيد نقطة |
| `seated-talk` | قاعد بيتكلم | seated-talk | كلام هادي طويل |
| `close-neutral` | نصف جسد طبيعي | close-neutral | قريب — الأساس |
| `close-explain` | نصف جسد يشرح | close-explain | قريب — شرح |
| `close-point` | نصف جسد يشير | close-point | قريب — إشارة |
| `close-thinking` | نصف جسد يفكر | close-thinking | قريب — تفكير |

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
```tsx
// engine R — src/lib/Presenter.tsx
import {MedoPresenter} from './lib/Presenter';
<MedoPresenter pose="explain" x={0.72} height={0.55} />
```
- `height` نسبة من 1920 (0.62 = 1190px). المكان بيتحدد من `place` في المانيفست: `feet` → `ground`
  (1390)، و`top` → `top` (190). تقدر تعدّل الاتنين من باراميترات `draw`.
- `PoseTrack` بتخلط بين المقاسين عادي — لكن الأفضل: **خليك جوه نفس الـframing في الجملة الواحدة**،
  والقطع بين مقاسين يبقى لحظة قرار (push-in/pull-out).
- `PoseTrack` بيعمل cross-fade **مشكّل** (القديم بيخرج في ٦٠٪ والجديد بيبدأ عند ٤٠٪) بمدة 0.12s —
  التغيير بيبان كـbeat cut مش كـdissolve باهت.
- `medo_wave` / `medo_think` / `medo_point` (الأسماء القديمة) بتتحوّل تلقائي للوضعيات الجديدة،
  فالمشاهد القديمة بقت بتستخدم الصور الحقيقية بدل الـplaceholder.

## الحياة الخفيفة | Idle life
بدون حركة، الصورة المقطوعة بتبان «ميتة». P/K بيضيفوا الأرقام نفسها (اختبار بيقارنهم)، وR حاليًا بيستخدم subset للتنفس والطلوع/النزول والميل الخفيف عبر `MedoPresenter`:

| الحركة | المعادلة |
|---|---|
| تنفّس | `1 + 0.008·sin(2π·0.28·t)` |
| طلوع/نزول | `2.5·sin(2π·0.22·t)` px |
| ميل جانبي | `2·sin(2π·0.13·t + 0.7)` px |
| ميلان الوضعية | `wave` 1.1° @1.05Hz · `clap` 0.6° @2.2Hz · `run/walk` 1.4° @1.6Hz · `shocked` نبضة سريعة |
| نبض إضافي | `run` 7px @1.6Hz · `walk` 3.5px · `shocked` ضربة واحدة عند كل ثانية |

## المشروع | New projects
`python3 tools/new_project.py <slug>` بينسخ `assets/poses/` + `poses.json` جوه المشروع لمحركَي P/K،
وبيضيف نسخة `public/assets/poses/` عشان Remotion (`staticFile()`) يقدر يحمل الصور.

## ملاحظة على المحرك K | Engine-K gotcha
`PoseTrack` بيحلّ الأسماء وقت الرسم (`at()`)، مش وقت الإنشاء — عشان تقدر تعرّف التراك في أول الملف
قبل `await loadPoses()`. لو حلّيتها بدري، أي وضعية مش في القائمة المدمجة هتقع على `neutral` بصمت.

## إضافة وضعية | Adding a pose
1. حطّ الأصل في `assets/poses/raw/<slug>.jpg` (خلفية فاتحة، الجسم كامل في الفريم).
2. ضيف سطر في `POSES` جوّه `tools/presenter_build.py` (العربي/الإنجليزي/التاجات/الميل).
3. `make poses` → شوف الشيت → لو محتاج تدوير/مقاس مختلف حط `scale` في السطر.
4. `python3 -m pytest tests/test_presenter.py` — بيتأكد إن القص نظيف ومفيش هالة بيضا.
