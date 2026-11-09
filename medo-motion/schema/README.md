# medo-motion/schema — مخططات العقود | Plan-file schemas

**الحالة:** قرار تسجيل (2026-11-09) · دي أول مخطط رسمي (`beats.schema.json`) لأقدم ملف خطة في الاستوديو.

## `beats.schema.json` — `plan/beats.json`

المصدر الوحيد للتوقيت في أي ريل: طول الفيديو = طول التعليق الصوتي المقاس، ولا يوجد أي رقم
طول مفروض من المخطط أو من أي أداة. المخطط هو **التوثيق الرسمي** للشكل (draft 2020-12) لأي
محرر/أداة خارجية تقرأ الملف. داخل الريف، الفحص الفعلي بيتم بـ:

```bash
python3 tools/beats_check.py projects/<slug>          # أو مسار الملف مباشرة
python3 tools/beats_check.py <beats.json> --quiet     # للفشل فقط (في السكربتات)
```

`tools/beats_check.py` stdlib-only (مفيش `jsonschema` في الاعتماديات) وبيفرض الاتنين:
**الشكل** — مفاتيح معروفة بس (`additionalProperties: false`)، الأنواع، `theme ∈ {dark, light}`،
`events[] = {t ≥ 0, what}` — **والدلالات** اللي JSON Schema ما بيقدرش يعبّر عنها:
`bounds` تبدأ عند 0 وغير تنازلية، طولها = المشاهد + 1 وتطابق `start/end` لكل مشهد،
`scenes` متتابعة من 1 وبدون فجوات/تداخل، `frames == round(duration × fps)` على المستويين،
`events[].t` جوّه حدود مشهدها، والـ`id` بدون تكرار.

### الشكلين الشرعيين

1. **draft** — مسودّة `tools/new_project.py` قبل قياس الصوت: `{"duration": null, "scenes": [], "note": "…"}`.
2. **measured** — ناتج `tools/vo_length.py --json` بعد القياس (+ ما يضيفه الوكيل: `theme`, `events`, `id`, `ui`).

أي حاجة تانية = فشل `beats_check.py` (ووسّعه أنت بس لما تضيف حقول جديدة: حدّث المخطط +
الفاحص + `tests/test_beats_schema.py` مع بعض).

### حدود المخطط

- `reel_lint.py` يفضل بوابة الحرفة فوق المخطط (S01–S05: contiguity، first start 0، last end == duration،
  طول مشهد ≤ min shot، `U01` للشاشات). المخطط يقول «الشكل قانوني»، الـlint يقول «الخطة تلعب».
- معنى الحقول بإيجاز: `clock` مش موجود في الملف — كل الأزمنة `vo_seconds` على ساعة الـVO.
  (`machines/*.json` هي اللي بتحمل `revealWindow` بوحدة صريحة: `vo_seconds` في الخطة، و`scene_seconds` بعد التحويل للمشهد.)
- `frames` على المستوى العلوي = `round(duration × fps)` وبيجمع فريمات المشاهد.
- `bad` fixture في `tests/fixtures/reel/bad/` **بيعدّي** المخطط فشل الحرفة بيبقى في الـlint — ده مقصود.

## الاختبارات

```bash
python3 -m pytest tests/test_beats_schema.py
```

بتغطي: كل fixture/مثال في الريف بيعدّي، ناتج `vo_length.py` بيرجع للمخطط سليم، ومصفوفة لمسات
(٢٣ حالة) كل واحدة بتفشل برمزها (`B01`–`B07`)، وتطابق المخطط ↔ الفاحص (المفاتيح، الـenums،
`additionalProperties`).
