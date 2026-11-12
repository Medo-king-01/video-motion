# محرّكا K وHybrid: عقد واحد، وصدق مختلف

**الحالة:** منفّذ (2026-11-12) · **الكود:** `tools/adapter_k.py` · `tools/adapter_hybrid.py`
**الاختبارات:** `tests/test_adapter_k.py` (5) · `tests/test_adapter_hybrid.py` (7) · `tests/test_render_backend_contract.py` (13)

`docs/editor-architecture.md §7` جمّد العقد قبل وجود أي adapter. P نفّذه ويرسم. الملف ده بيسجّل
إيه اللي K وHybrid **بيعملوه فعلًا** النهارده، وإيه اللي بيرفضوه، وليه الرفض ده هو الشكل الصحيح
للمرحلة الحالية مش نقصًا فيه.

## 1. K — يقرأ ويتحقق، ويرفض إنه يرسم

| القدرة | الحالة المعلنة | الواقع |
|---|---|---|
| `project.read` | supported | `compile()` بيعدّي على `compile_project` (نفس مدقّق P)، والمشروع الغلط بيرجع `InvalidProject` |
| `graph.execute` | **unsupported** | `preflight()` بترجّع `unsupported` مع `R11` |
| `range.render` · `alpha.layer` · `text.arabic` · `offscreen.render` · `transitions.catalog` | unsupported | `render()` بيرمي `AdapterError("R11", …)` وبس — مفيش إطار واحد بيتكتب |

`R11` رسالتها: «engine K has no wired pixel path in this build». يعني الـadapter موجود، والمسار
اللي بيرسم لسه مش موصول بـNode/Remotion. **ليه نشحنه وهو ما بيرسمش؟** لأن البديل مش الصمت: بوّابة
`tools/backend_capabilities.py` بترفض أي ادّعاء `project.read` من محرّك مالوش `adapter_<x>.py`،
والمحرر بيسأل كل محرّك نفس السؤالين. K بقى بيرد على الاتنين بصدق.

`node_available()` بيقول هل الـtoolchain موجود على الجهاز (`--toolchain`)، فلو المالك فتح المشروع على
جهاز فيه Node عرف إن الناقص هو الوصلة مش البيئة.

## 2. Hybrid — قرار التوجيه كبيانات

Hybrid مش راسم تالت؛ هو **التركيب**: كل مسار في المشروع بيتحوّل لمحرّك يقدر يرسمه، والقرار ده
بيتكتب في الـgraph نفسه:

```json
"routing": [
  {"trackId": "v1", "kind": "video", "backend": "P",
   "reason": "the only backend with a wired pixel/sample path in this build"}
]
```

- `compile()` بيضيف `routing` و`graphSha256`، و`executable` بيبقى `true` بس لما كل مسار فعّال يلاقي
  محرّكًا.
- `preflight()` بيجمع رفض التوجيه (`R12`) مع رفض P نفسه، فالمستخدم بيشوف السبب الصحيح مش آخر واحد.
- `render()` بيفوّض لـP وبيحط `routing` + `routedBy: "Hybrid"` في الـmanifest الراجع، فمفيش ادّعاء
  ببكسلات من مصدر تاني.
- المسار المعطّل مش بيتوجّه ومش بيترفض (مالوش مساهمة). المسار الفاضي كذلك.
- المسار اللي محدش يقدر يرسمه (زي `graphics` وفيه مقاطع) بيرجع `R12` بدل ما يتشال بصمت. **ملاحظة
  صريحة:** العقد الحالي بيرفض أصلًا مشروعًا فيه مقطع graphics (`U05`)، فـ`R12` حارس احتياطي
  للمخططات اللي تجي من مستورد مستقبلي — مفيش مشروع صالح بيوصله النهارده، والاختبار بيستدعيه على
  graph مباشرةً.

### اللي بيتغيّر لما K يرسم

دالة واحدة: `route()`. أول ما K ياخد مسار بكسلات، المسارات اللي بتتقسم بين الاتنين بتتكتب في نفس
الجدول، والاختبارات (`test_every_drawing_track_routes_to_the_backend_that_can_draw_it`) بتفشل لو
القرار ما اتعكسش في `routing`.

## 3. الحالة في `render_backend.py --check`

```
OK: 3 real adapter(s) (Hybrid, K, P) and 1 null adapter(s) (R) keep the contract.
```

`REAL` في `tools/render_backend.py` هو سجل الـadapters الموجودين؛ كل اسم مش موجود فيه بيتفحص بـ
`NullAdapter` (رافض، صادق، وبلا رسم). R لسه هناك لحد ما يتقرّر مصيره.

## 4. الحدود

- K ما بيرسمش، وHybrid ما بيرسمش أكتر من P — **مفيش تكافؤ بكسلات مع Remotion**، ومفيش ادّعاء إن
  K «بيشتغل على جهاز المالك».
- Hybrid بيرسم بكسلات P بالكامل، فاللي P بيرفضه (`R02`, `R03`, `R07`, `R08`…) Hybrid بيرفضه كذلك.
- الـ`routing` مبنى على نوع المسار فقط؛ تقسيم **داخل** المسار (نصف المقاطع على K والنصف التاني على P)
  مش منفّذ ولا مدّعى.
