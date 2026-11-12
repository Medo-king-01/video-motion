# المحرّك R (Remotion) خلف العقد — بيقرا، وبيقول بالظبط إيه الناقص

**الحالة:** منفّذ (2026-11-12) · **الكود:** `tools/adapter_r.py`
**الاختبارات:** `tests/test_adapter_r.py` (7) · **الـmanifest:** `medo-motion/schema/backend-capabilities.json`

قبل كده R كان `NullAdapter` عام: بيقول «مش مدعوم» من غير ما يقول ليه. ده كان مقبول طول ما السكافولد
موجود والفكرة إن الرندر لسه مش موصول؛ بس `NullAdapter` مش بيفرّق بين **نقص تنفيذ** (مفيش جسر بين
graph المشروع الموحّد ومشهد Remotion) و**نقص بيئة** (الباكدجات pinned مش متسطّبة). المشغّل محتاج يعرف
الفرق، فالـR بقى adapter حقيقي برسالتين منفصلتين.

## 1. إيه اللي بيعمله

| الخطوة | النتيجة |
|---|---|
| `compile(project)` | graph المشروع من نفس الكومبايلر، `executable: false`، `backend: {name: "R", version: "0.1.0"}`, `graphSha256` |
| `preflight(graph)` | `status: "unsupported"` + `diagnostics` + `toolchain` |
| `render(...)` | بيرمي `AdapterError` بأول كود تشخيص، وما بيكتبش أي ملف |
| `capabilities()` | من الـmanifest: `project.read: supported`، `graph.execute: unsupported` |

## 2. الأكواد

| الكود | المعنى | إمتى |
|---|---|---|
| `R13` | مفيش جسر بين الـgraph الموحّد ومشهد Remotion؛ R بيرندر `plan/beats.json` بتاعه | **دائمًا** لحد ما الجسر يتكتب |
| `R14` | الـtoolchain (npm pinned) مش متسطّب في الشيك‑أوت | لما `node` أو `@remotion/renderer` أو كروم مش موجودين |

`toolchain()` بيقيس الجهاز فعلًا:

```json
{"node": "/usr/bin/node", "npm": "/usr/bin/npm", "scaffold": true,
 "dependencies": {"remotion": true, "@remotion/cli": true, "@remotion/renderer": true, "react": true},
 "allDependencies": true, "chrome": null, "renderable": false}
```

`renderable = node && @remotion/renderer && chrome` — وكروم مش جزء من السكافولد، عشان كده `R14` بتظهر
كتير، وده مقصود.

## 3. الاستخدام

```bash
python3 tools/adapter_r.py --capabilities                     # عقد القدرات
python3 tools/adapter_r.py --toolchain                        # إيه اللي متاح على الجهاز ده
python3 tools/adapter_r.py projects/demo/project.json --preflight   # exit 1 والتشخيصات
python3 tools/render_backend.py --check                       # 4 real / 0 null
```

## 4. اللي **متأكدين** منه

- `conformance_problems(RAdapter()) == []` — نفس الشكل اللي P وK وHybrid بيجيبوه.
- `compile` بيرجّع graph صالح من نفس الكومبايلر، ومعلّم إنه **غير قابل للتنفيذ** — مفيش ادّعاء رندر.
- `render` بيرفض وما بيكتبش أي ملف (الاختبار بيتأكد إن المسار مش موجود بعد الرفض).
- الـcapability gate بيفضل شغال: اختبار `test_claiming_graph_execution_before_an_adapter_fails`
  بيحاكي غياب الـadapter (monkeypatch لـ`adapter_path`) وبيتأكد إن الادّعاء بيترفض.

## 5. اللي **مش** متأكدين منه

- **مفيش رندر R اتحقق منه**: مفيش مشهد Remotion موصول بالمشروع، فمفيش إطار واحد اتولد من R.
  `docs/remotion*.md` بتوصف السكافولد بتاعه، مش تكامل.
- **مفيش npm install اتجرب في الـCI**: الـ`R14` بتقيس الوجود، مش بتسطّب حاجة.
- لو الـtoolchain اتسطّب، `R14` بتختفي لكن `R13` بتفضل — لأن الجسر لسه مش مكتوب.
