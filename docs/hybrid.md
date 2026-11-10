# Hybrid P/K/R reels

A hybrid project combines the three renderer strengths within one timeline: P for presenter/explainer imagery, K for Canvas and kinetic typography, and R for React/Remotion compositions. Version 1 uses **sequential full-frame segments**. Each segment has exactly one rendering engine; simultaneous layers or importing one engine's feature catalog into another are out of scope.

Create the scaffold with `python3 tools/new_project.py <slug> --engine hybrid`. It preserves all three source engines in the project and creates `plan/hybrid.json`. Configure integer, half-open frame ranges at 30 fps, edit each engine's own scene data, and run `python3 ../../tools/render_hybrid.py --project .` from the project root. The renderer validates continuous coverage, exact segment frame counts, 1080×1920 size, 30 fps, and final duration. It adds the optional single soundtrack only after picture assembly and refuses to overwrite an existing final file.

The project-local operator guide, schema example, setup notes, and scope boundaries are in [`medo-motion/templates/HYBRID.md`](../medo-motion/templates/HYBRID.md); the scaffold copies it to `HYBRID.md`. Run `python3 tools/selftest.py --hybrid` to exercise short P, K, and R segments, assembly, and audio muxing end to end. This smoke test does not claim that unported P/K effects exist in R.

## v2 — طبقة شفافة متزامنة (K فوق P)

النسخة 1 كانت **مقاطع متتالية**: كل لحظة يملكها محرك واحد. النسخة 2 تفتح ما لا يعمله محرك واحد:
مقطع P كامل الخلفية، وفوقه طبقة K **شفافة** متزامنة — تايبوغرافي حركي أو واجهة Canvas فوق لقطات
البريزينتر. الشكل في `plan/hybrid.json`:

```json
{"version": 2, "duration_frames": 90, "segments": [
  {"id": "intro", "start_frame": 0, "end_frame": 60,
   "layers": [{"engine": "p"}, {"engine": "k", "alpha": true}]},
  {"id": "outro", "start_frame": 60, "end_frame": 90, "engine": "r"}
]}
```

القواعد التي يفرضها `tools/render_hybrid.py` (ورفضها صريح لا صامت):

- `engine` و`layers` في نفس المقطع مرفوضان — استخدم واحدًا.
- الطبقة الأولى **أساس معتم** (P أو R أو K بلا alpha)؛ الطبقة الثانية **K فقط** وبـ`alpha: true`.
- حتى **4 طبقات K** فوق الأساس؛ `--alpha` على P/R مرفوض.
- ملفات v1 تُطبَّع تلقائيًا إلى `layers`، فلا مشروع قديم ينكسر.

التنفيذ: أساس يُرندَر كاملًا (mp4)، ثم طبقة K تُرندَر كتسلسل PNG شفاف
(`node src/render.js … --alpha`؛ `main.js` يستدعي `clearRect` بدل تعبئة الخلفية السوداء)،
ثم `ffmpeg -filter_complex "[0:v][1:v]overlay=format=auto"` يدمجها بإطارات مضبوطة
(`-frames:v` من فرق الإطارات وليس من `-shortest`). الملف النهائي يُكتب عبر ملف مؤقت و`os.replace`،
و`--profile` يسجّل عدد الـ`overlays` لكل مقطع.

الحدود المقصودة: لا دمج أكثر من طبقتين، ولا alpha على P/R. الطبقة الشفافة تحتاج خلفية معتمة
تحتها؛ وإلا فالحل مقطع P ثم مقطع K متتاليًا (v1).

## v2.1 — طبقة بـmasking (النص «من ورا» الميدو)

v2 كانت بتحط النص **فوق** البريزينتر دايمًا. v2.1 بتخلي طبقة K تمر **من وراه**: الطبقة بتاخد
`mask` ساكنة، والقاعدة إن **الأبيض بيرجّع الصورة للأساس** (الماسك هو «اللي الأساس بيكسبه»)،
والأسود بيسمح للطبقة تظهر. التنفيذ رياضي: `alpha(K) × (1 − mask)` جوّه ffmpeg، مش رسم فوق بعض.

```json
{"version": 2, "duration_frames": 60, "segments": [
  {"id": "intro", "start_frame": 0, "end_frame": 60,
   "layers": [{"engine": "p"},
              {"engine": "k", "alpha": true,
               "mask": {"type": "rect", "x": 0.34, "y": 0.42, "w": 0.32, "h": 0.58, "feather": 10}}]}
]}
```

- `rect`: كسور من الكادر (`x`,`y`,`w`,`h` بين 0 و1) + `feather` بالبكسل (0–120). الـfeather
  بيتنفّذ كـ`gblur` على الماسك، فالحافة بتبقى انتقال ناعم مش قطع.
- `image`: ملف matte ‏1080×1920 **داخل المشروع** (`white = الأساس يكسب`)، بيتحوّل لـgray
  وبيتقرأ كـinput تالت. المسار المطلق أو اللي بيطلع بره المشروع مرفوض، والملف الغائب بيفشل
  **قبل** أي لمس للأساس.
- الماسك ساكن للمقطع كله (مافيش matte متحرك لكل إطار بعد)؛ كل طبقة ممكن تاخد ماسكها المستقل.
- الماسك على أساس معتم أو طبقة من غير `alpha` **مرفوض** — ماسك مش بيتنفّذ لازم يفشل بصوت.

الـfiltergraph بيبقى:

```
[0:v]format=yuv420p,setsar=1[mb];
[1:v]format=rgba,setsar=1,split=2[ov][ova];
[ova]alphaextract[ka];
color=c=black:...,drawbox=...,format=gray,gblur=sigma=…,negate,setsar=1[mi];
[ka][mi]blend=all_mode=multiply[am];
[ov][am]alphamerge[ovm];
[mb][ovm]overlay=format=auto
```

التحقق: `tests/test_hybrid_masks.py` (24 اختبار وحدة: العقد + الرسم البياني) و
`tests/test_hybrid_layers.py` (4 اختبارات بكسل حقيقية: المستطيل، الـfeather، الـmatte، والملف
الغائب). وعلى مشروع حقيقي: نفس المشهد بماسك وبدونه اختلف **داخل** المستطيل بمقدار 57.5
(متوسط فرق البكسل) و**خارج** المستطيل بـ0.0 بالظبط — يعني الطبقة اتشالت من المنطقة المطلوبة
بالظبط ومفيش حاجة تانية اتغيرت.

> **حراسة العقد:** القدرات التي يفرضها `tools/render_hybrid.py` معلنة في `CAPABILITIES`، وكل واحدة
> موسومة في `AGENTS.md` و`medo-motion/templates/HYBRID.md` بـ`CAP:<name>`؛ واختبار
> `tests/test_capability_contract.py` يفشل لو أُضيفت قدرة بلا توثيق أو بقي توثيق لقدرة أُزيلت.

## v2.2 — أكثر من طبقة K فوق الأساس

الطبقة الواحدة بتحل «نص فوق الميدو»، لكن الريل الحقيقي بيحتاج **أكتر من مستوى**: تايتل فوق،
كارت تحت، شارة على الجنب. v2.2 بتسمح لحد **4 طبقات K** فوق أساس واحد، وبتتحل مشكلة جوهرية:
المشروع الواحد فيه **شجرة K واحدة**، فإزاي طبقتين يطلعوا صورتين مختلفين؟ الإجابة: كل طبقة بتقول
اسم السين/المشاهد اللي بترسمها.

```json
{"id": "intro", "start_frame": 0, "end_frame": 90,
 "layers": [{"engine": "p"},
            {"engine": "k", "alpha": true, "scenes": ["title"]},
            {"engine": "k", "alpha": true, "scenes": ["chart"],
             "mask": {"type": "rect", "x": 0.32, "y": 0.42, "w": 0.36, "h": 0.52, "feather": 8}}]}
```

القواعد اللي بيفرضها `tools/render_hybrid.py`:

- الطبقات بتتراكب **من تحت لفوق** بترتيب كتابتها؛ آخر طبقة هي العليا.
- أول ما يبقى فيه أكتر من طبقة، **كل** طبقة لازم تسمّي `scenes`؛ طبقة من غير أسماء = رفض صريح
  (مش «ترندر نفس الصورة مرتين»).
- السين الواحد ملك طبقة واحدة: لو اتكرر في طبقتين → خطأ خطة بيقوله بالأرقام.
- `scenes` على الأساس أو على طبقة من غير `alpha` مرفوض.

التنفيذ: `render.js` بياخد `--only a,b` وبيتحقق من الأسماء **قبل** ما يفتح المتصفح (اسم غلط =
فشل فوري مش تعليق 30 ثانية)، و`main.js` بيرسم بس المشاهد المسموحة ويسيب الباقي شفاف. بعدين
**composite واحد** لكل المقاطع: كل تسلسل PNG بيتحوّل لـinput، وكل طبقة ليها سلسلة overlay خاصة
بماسكها لو موجود — مش pass ترميز لكل طبقة، عشان الأساس مايتدهورش جيل ورا جيل.

التحقق: على مشروع حقيقي بطبقتين (`scenes: ["example"]` و`scenes: ["arabic-example"]` وماسك على
التانية) — تغطية الطبقة الأولى: **100% عند t=0.5s و0% عند t=2.5s**، والتانية العكس بالظبط،
والملف النهائي 90 إطارًا @30fps بفتحة ترميز واحدة. الاختبارات: `tests/test_hybrid_stack.py`
(17 اختبار وحدة) و`tests/test_hybrid_layers.py` +4 (طبقتين بالألوان، ماسك على العليا، و`--only`
حقيقي على Chromium، ورفض اسم سين مجهول).

## درافت سريع

`python3 tools/pipeline.py <project> --draft` (أو `render_hybrid.py --draft` مباشرة) بيرندر نفس
الخطة على 540×960 @15fps في `out/hybrid-draft.mp4`. الأساس P بياخد `--draft` (إطار من كل اتنين)،
الأساس K والطبقات الشفافة بياخدوا `--fps 15 --scale 0.5`، والماسك بيتبني على كانفس 540×960.
الأساس R مرفوض، والدرافت مابيدخلش QA ولا mux ولا بيلمس الماستر. التفاصيل والأرقام في
`docs/preview.md`.

## ملاحظة تشغيل

طبقة K محتاجة Chromium و`playwright-core`. `render_hybrid.py` بقى يحلّها لوحده بدل ما يفشل جوه
Node برسالة `Cannot find module 'playwright-core'`:

1. لو `MEDO_TOOLKIT`/`MEDO_CHROMIUM` متظبطين في البيئة → بيحترمهم زي ما هما (مش بيلمسهم).
2. لو مش متظبطين → بياخد `tools/toolkit` لو فيه `node_modules/playwright-core`، ويسأل
   `node tools/chromium.mjs --json` عن الـChromium المرفق. الـhelper ده **بيفك ضغط** المتصفح من
   حزمة npm المحلية، **ما بينزّلش** حاجة.
3. لو الاتنين مش موجودين → مابيفشلش من نفسه؛ الـK render هو اللي بيقول الرسالة، والريل اللي كله
   P/R بيكمّل عادي على جهاز من غير Chromium.

التحقق: تشغيل من شل نضيف (`env -u MEDO_TOOLKIT -u MEDO_CHROMIUM -u LD_LIBRARY_PATH`) على مشروع
hybrid بطبقة K وماسك → `HYBRID OK · 1 layered, 1 K overlay(s) (1 masked) · 30 frames` في 31s.
