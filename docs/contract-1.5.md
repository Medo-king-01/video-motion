# العقد 1.5: نص بلونين في سطر واحد، وتحريك حرف‑بحرف

**الحالة:** منفّذ (2026-11-12) · **الـschema:** `medo-motion/schema/unified-project.schema.json`
**الفحص:** `tools/unified_project_check.py` (`U12`) · **الترحيل:** `tools/unified_project_migrate.py` (`CURRENT = "1.5"`)
**الاختبارات:** `tests/test_contract_15.py` (14) + `tests/test_unified_reference_preview.py` (11)

العقد 1.4 كان بيعرف ينصّف النص لفئات: كل بلوك نص ليه لون وحجم واحد، والتحريك كان كلمة‑كلمة. الطلب
الحقيقي على الريلز أسوأ من كده: كلمة واحدة بلون، الباقي أبيض، والحركة تبدأ حرف‑بحرف. الـ1.5 بيضيف
الاتنين كتمثيل صريح في المشروع — مش كـCSS ولا كـoverlay على الفيديو — عشان أي محرّك (P/Motion) يرسمهم
بنفس المعنى.

## 1. الـruns: أجزاء من النص بلون/حجم/خط مختلف

```json
{
  "id": "cap1",
  "value": "العنوان الأول بيتحرك حرف بحرف",
  "animation": {"kind": "letters-up", "stagger": 24000, "ease": "cubic-out"},
  "runs": [
    {"start": 0, "end": 7, "color": "#ffab00"},
    {"start": 8, "end": 13, "color": "#6ee7ff", "size": 44}
  ]
}
```

- `text.runs` مصفوفة حتى **16** عنصر، وكل `run` فيه `start` و`end` (إلزاميًا)، واختياريًا `color`
  (`#rrggbb`)، `size` (8–400)، `font`. `additionalProperties: false` — أي حقل تاني يُرفض.
- `start` و`end` **إزاحات حروف** في `text.value` (`0 <= start < end <= len(value)`).
- الإنماط **تتراكم**: الكلمة اللي وسط run بلون بتاخد `color`/`size`/`font` من الـrun، وأي حقل مش
  موجود بيرجع لقيمة البلوك.

### `U12` — الفحص (6 رسائل رفض)

| الحالة | الرسالة |
|---|---|
| `runs` مش مرتبة تصاعديًا | `runs must be sorted by start` |
| تراكب بين run‑ين | `runs must be sorted and must not overlap` |
| `start >= end` | `run.start must be smaller than run.end` |
| `end` أطول من النص | `run.end is longer than text.value` |
| البداية أو النهاية **وسط كلمة** | `a run must start/end at a word boundary` |
| run مبيغيّرش حاجة (نفس لون/حجم/خط البلوك) | `run changes nothing` |

قاعدة حدود الكلمة مقصودة: قصّ نص عربي وسط كلمة بيكسر وصل الحروف (شكل الحرف بيتغيّر حسب جيرانه)،
فالعقد بيرفضه من الأول بدل ما كل محرّك يقرّر لوحده.

## 2. التحريك: `letters-up` و`letters-fade`

`animation.kind` بقى: `none` · `fade` · `words-up` · `words-fade` · `letters-up` · `letters-fade`.

- الفرق بين `words-*` و`letters-*` هو **وحدة التتابع**: كلمة كاملة أو حرف (cluster من HarfBuzz).
- `stagger` هو المسافة بالـticks بين بداية كل وحدة، و`ease` = `linear` | `cubic-out`.
- **الوصل محفوظ**: الكلمة بتتشكّل مرة واحدة بـHarfBuzz، وكل cluster بيتقصّ من نفس الـcanvas، فالحروف
  المتصلة (ـتـ، ـيـ، لا) بتنزل كوحدات شكلها زي ما هي — مش حروف منفصلة بترتيب منطقي مقلوب.
- `letters-*` بيحتاج **حرفين على الأقل** في النص وإلا `U11` بترفض (`letters animation needs at least
  two letters`)؛ `words-*` بيحتاج كلمتين.
- الاتجاه: مع `direction: "rtl"` أول وحدة تظهر عند **يمين** السطر، والـ`words-*`/`letters-*` بتحسب
  الترتيب من البداية المنطقية للنص.

الترتيب في الكود: `arabic_shape.text_clusters()` بيرجّع `[{cluster, sprite, x, y, width}]` بإحداثيات
canvas الكلمة، و`_text_layers` في `tools/unified_reference_preview.py` بيرسمهم في نفس الصندوق اللي
بيرسمه البلوك الثابت — فالحركة وهي خالصة بتطلع نفس الصورة بالظبط (اختبار
`test_the_finished_letter_animation_is_the_plain_word` بيقارن الصندوق والبكسلات).

## 3. التصدير

P بيرسم الـruns والحركة الحرفية في **المعاينة وفي التصدير** بنفس الدالة، فالإطار اللي بتشوفه في المحرر
هو الإطار اللي بيتكتب في الـMP4 (مفيش مسار تاني للتصدير).

## 4. الترحيل من 1.4

`1.4 → 1.5` بيضيف `schemaVersion` وبس: مفيش `runs` ولا `animation.kind` جديد بيتزرع تلقائيًا، فمشروع
1.4 بيتحوّل بدون أي تغيير في المعنى (اختبار `test_a_14_project_migrates_and_keeps_its_texts`).
المشاريع الأقدم من كده بتعدي على خطواتها بالترتيب (1.0 → … → 1.5) في نفس الاستدعاء.

```bash
python3 tools/unified_project_migrate.py projects/demo/project.json          # يحوّل ويكتب
python3 tools/unified_project_check.py projects/demo/project.json            # لازم U12 يعدّي
```

## 5. اللي مش داخل العقد (بصراحة)

- **مفيش **traits** عامة** (ظل، حدود، تدرّج داخل النص) ولا محاذاة لكل run؛ الـrun بيغيّر لون/حجم/خط بس.
- **مفيش** تشكيل يدوي (tashkeel) مضمون: النص بيتشكّل من الفونت؛ الـruns بتقسّم **نفس** النص، مش بتغيّره.
- **مفيش** `letters-*` مع `wrap` على مستوى الحرف عبر سطرين: الكلمة بتتشكّل كوحدة، فلو الكلمة أطول من
  السطر بتتصغّر (shrink-to-fit) بدل ما تتقطّع.
- **مفيش** تحريك لكل run‑لوحده (كل بلوك ليه `animation` واحد).
