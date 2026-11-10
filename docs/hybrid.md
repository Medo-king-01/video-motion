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
- طبقة واحدة كحد أقصى فوق الأساس؛ `--alpha` على P/R مرفوض.
- ملفات v1 تُطبَّع تلقائيًا إلى `layers`، فلا مشروع قديم ينكسر.

التنفيذ: أساس يُرندَر كاملًا (mp4)، ثم طبقة K تُرندَر كتسلسل PNG شفاف
(`node src/render.js … --alpha`؛ `main.js` يستدعي `clearRect` بدل تعبئة الخلفية السوداء)،
ثم `ffmpeg -filter_complex "[0:v][1:v]overlay=format=auto"` يدمجها بإطارات مضبوطة
(`-frames:v` من فرق الإطارات وليس من `-shortest`). الملف النهائي يُكتب عبر ملف مؤقت و`os.replace`،
و`--profile` يسجّل عدد الـ`overlays` لكل مقطع.

الحدود المقصودة: لا masking، ولا دمج أكثر من طبقتين، ولا alpha على P/R. الطبقة الشفافة تحتاج
خلفية معتمة تحتها؛ وإلا فالحل مقطع P ثم مقطع K متتاليًا (v1).

> **حراسة العقد:** القدرات التي يفرضها `tools/render_hybrid.py` معلنة في `CAPABILITIES`، وكل واحدة
> موسومة في `AGENTS.md` و`medo-motion/templates/HYBRID.md` بـ`CAP:<name>`؛ واختبار
> `tests/test_capability_contract.py` يفشل لو أُضيفت قدرة بلا توثيق أو بقي توثيق لقدرة أُزيلت.
