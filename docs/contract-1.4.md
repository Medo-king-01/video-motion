# العقد 1.4: تحريك النص، الـwipe، وحدود النص المكتوبة

**الحالة:** منفّذ (2026-11-12) · **المخطط:** `medo-motion/schema/unified-project.schema.json` (`schemaVersion: "1.4"`)
**المدقّق:** `tools/unified_project_check.py` (`U08`–`U11`) · **الهجرة:** `tools/unified_project_migrate.py` (`CURRENT = "1.4"`)
**الاختبارات:** `tests/test_contract_13.py` (12) · `tests/test_migrate_autosave.py` (11) · `tests/test_unified_project.py` (22)

العقد 1.3 فتح باب النص والسرعة والـstreams. النسخة 1.4 تقفل الباب على **كيف يتحرّك النص** و**كيف
يظهر الانتقال** بدل ما تسيبه اتفاقًا شفويًا بين المحرّكين. كل حقل هنا **اختياري**: مشروع 1.0–1.3
يفضل صالحًا زي ما هو، والهجرة بتضيف بس اللي العقد الجديد بيفرضه.

## 1. اللي اتضاف في 1.4

| الحقل | الشكل | القاعدة | الكود |
|---|---|---|---|
| `text.wrap` | boolean | يلفّ الكلمات على سطور بقياس الشيبـر (هامش = `max(8, width/12)`) | — |
| `text.animation` | `{kind, stagger, ease}` | `kind ∈ {none, fade, words-up, words-fade}` · `stagger` 0–240000 tick · `ease ∈ {linear, cubic-out}` | `U11` |
| `transition.kind = "wipe"` | + `direction ∈ {left, right, up, down}` | الـwipe **لازمه** اتجاه، والـcrossfade **مايصحّش** يكون له اتجاه | `U07` |
| `transition` على مسار صوت | — | ممنوع: الصوت مالوش هندسة تُمحى | `U07` |
| `effect.type = "opacity"` على مسار نص | — | مسموح (كان فيديو فقط) | `U06` |

`U11` بيمنع تلات حاجات: `kind: "none"` مع أي توقيت (تناقض)، و`words-*` على نصّ فيه كلمة واحدة
(مفيش تعاقب)، و`stagger` خارج المدى. `U10` (من 1.3) بيفضل شغّالًا: اتجاه النص لازم يطابق حروفه.

## 2. الدلالة المقاسة — مش وصف

المرجع هو `tools/unified_reference_preview.py`، والـadapter P بيرسم بنفس الدالة، فالكلام هنا
مقيس بالبكسل:

- **اللفّ**: الكلمات بتتقاس واحدة واحدة بالشيبـر (`arabic_shape`)، وأول كلمة تكسر السطر بتبدأ سطرًا
  جديدًا. لو الكتلة أطول من الإطار بتصغر بنسبة واحدة، والسطر الأعرض من المساحة بيتقلّص لوحده.
- **التعاقب**: الكلمة رقم `i` بتبدأ عند `i × stagger` من بداية المقطع، وبتوصل 100% عند
  `(i+1) × stagger`، والتقدّم بيتعدّل بـ`cubic-out` (`1000 − (1000−p)³/10⁶`). `stagger = 0`
  معناه «كل الكلمات مع بعض» — إظهار فوري، مش تعاقب لا نهائي.
- **`fade`**: شفافية الكلمة بتطلع من 0 لـ255 بالتكبير على قناة alpha فقط؛ اللون ما بيتغيّرش.
- **`words-up`**: نفس التلاشي + نزول الكلمة بمقدار `size × (1 − p)` بكسل من موضعها النهائي، فبتطلع
  من تحت لفوق.
- **الـwipe**: حدّ حاد (hard edge) بيتحرّك على طول المحور: عند `offset = 0` الصورة القديمة كلها، وعند
  `offset = length−1` الجديدة كلها. مفيش تلاشي ناعم ومفيش anti-alias — الـwipe هنا قرار شكل، والقرار
  إن الحدّ يبان حادًا.
- **الـcrossfade**: خلط صحيح (`(incoming·k + outgoing·(n−k) + n/2) / n`) بلا كسور عشرية، فالنتيجة
  حتمية على أي معالج.

## 3. الهجرة والحدود

- `CURRENT = "1.4"`، و`M01`–`M03` زي ما هي: مشروع غير صالح قبل الهجرة مرفوض، وإصدار أحدث مرفوض،
  والهجرة اللي تفشل في إعادة فحص نفسها مرفوضة. مشروع 1.3 بيتحوّل لـ1.4 من غير ما يتغيّر فيه حقل
  واحد (مفيش حقل إلزامي جديد).
- **مش مدّعى**: تحريك على مستوى الحرف (per-letter) — `U11` بيعرف `words-*` فقط؛ التنسيق الغني
  (bold/italic داخل النص)؛ لفّ بالكسور مع كشيدة؛ الـwipe بـmask ناعم أو بشكل غير مستطيل؛ soft-edge
  crossfade بلون gamma-correct.

## 4. إزاي تتحقق بنفسك

```bash
python3 tools/unified_project_check.py projects/demo/project.json      # لازم يعدّي
python3 tools/unified_project_migrate.py --check projects/demo/project.json
python3 -m pytest tests/test_contract_13.py tests/test_migrate_autosave.py tests/test_unified_reference_preview.py
```

`tests/test_unified_reference_preview.py` فيه إطاران مقاسان: إطار بيكشف نصف الـwipe (نصف بكسل من
كل صورة)، وإطار نص فيه كلمة ظاهرة وكلمة لسه ما وصلتش.
