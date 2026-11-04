# Machine Explainer — شرح الأنظمة والعتاد الهندسي (`P` / `K` / `R`)

مسار عمل أصلي (Native) داخل الاستوديو لبناء مشاهد **"إزاي بيشتغل؟"** للأنظمة والعتاد الهندسي
بقطع أيزومتري ثلاثي الطبقات (`back` / `mid` / `front`)، مع توثيق صارم للمصادر، وتزامن مقاس مع
`plan/word-timings.json`، وفحص حجب هندسي حقيقي بالأقنعة المسقطة (`X01`–`X04`) عبر المحركات التلاتة.

---

## ١) البنية والملفات

| الملف | الدور |
|---|---|
| `tools/machine_explainer.py` | تهيئة قالب مبدئي (`--init`) وفحص المشروع بالكامل (`--check` / `--max-occlusion` / `--json`) |
| `tools/reel_lint.py` | يشغّل بوابات `X01`–`X04` تلقائيًا عند وجود `plan/machines/*.json` في المشروع |
| `medo-motion/templates/procedural-reels/machine_kit.py` | محرك **P**: توسيع النماذج الأربعة + `custom`، الحالة النقية `machine_state_at`، الإسقاط وترتيب الرسام `build_machine_scene`، فحص الحجب النقطي `compute_occlusion_report`، فحص الغلاف الهندسي ومسارات الحركة `compute_envelope_report`، والرندر بـOpenCV + `draw_directed_text` |
| `medo-motion/templates/render/lib/machine-kit.js` | النواة المشتركة لمحركي **K** و**R** (متطابقة حرفيًا مع نسخة `remotion/src/lib/machine-kit.js`) |
| `medo-motion/templates/render/lib/machine-visual.js` | محول محرك **K** (Canvas2D + `protectBox` + `drawDirectedText` + `safeEnvelope`) |
| `medo-motion/templates/remotion/src/lib/layout.tsx` | طبقة تدقيق التخطيط في محرك **R** (`ProtectBox` + قياس أسطر النص العربي الملتفة والتحويلات الحركية فعليًا عبر `collectDomLayoutBoxes` + فحص `auditLayout` للقواعد `L00`–`L04`) |
| `medo-motion/templates/remotion/src/lib/MachineDiagram.tsx` | مكون محرك **R** (`<svg>` + `<ProtectBox>` + `<DirectedText>`) مع تدقيق التخطيط الاختياري الصارم `strictLayout` |

---

## ٢) النماذج الهندسية الأربعة الجاهزة + `custom`

1. `nvme_ssd`: لوحة `pcb`، أطراف ومسارات `pcie_bus`، متحكم `controller`، ذاكرة `dram_cache`، قنوات `nand_channel`، شرائح `nand_stack` متعددة الطبقات، ومشتت مقطوع `heatsink`.
2. `cpu_package`: قاعدة `substrate`، نقاط توصيل `socket_pins`، أنوية `cores`، كاش مشترك `l3_cache`، شريحة `io_die`، جسر ربط `fabric`، وغطاء حراري مقطوع `ihs`.
3. `ram_dimm`: لوحة `pcb`، أطراف `bus_pins`، متحكم `rcd_controller`، قناتا نقل `channel_bus`، مجموعات `dram_banks`، ومشتت مقطوع `heatspreader`.
4. `cooling_system`: قاعدة تلامس `coldplate`، أنابيب حرارية `heatpipes`، مصفوفة زعانف `fin_stack`، مروحة دوارة `fan` بسبع ريش حتمية `f(t)`، وغطاء مقطوع `shroud` مع تيارات هواء `airflow_stream` تُرسم بعد طبقة `front`.
5. `custom`: تعريف حر لـ`parts[]` و`paths{}` و`world{}` بنفس البدائيات (`slab`، `slab_stack`، `cylinder`، `ring`، `ticks`، `wire`).

---

## ٣) عقد البيانات والتوقيت (`plan/machines/<id>.json`)

- **مرجعية كل ادعاء (`X01`)**:
  - `evidence: "source" | "user"`: يشترط `sourceId` موجود في `sources[]` (مع `ref` قابل للتحقق: URI أو DOI أو كود معياري مثل `JESD79-5C`) + `locator: { kind: "section" | "page" | "table" | "figure" | "clause" | "line", value }` + اقتباس نصي داعم `quote`.
  - `evidence: "illustrative"`: مسموح فقط بتصريح صريح `disclaimer` + وسم شاشة صريح `illustrativeLabelId` داخل `copyIds`، ويُمنع تمرير أرقام مواصفات غير موثقة داخل نص الشاشة المرتبط بالخطوة.
  - الأجزاء غير الموثقة تُرسم صامتة كسياق بصري بدون ادعاء نصي.
  - **حدود فحص `X01` (أوفلاين بالكامل):** يتحقق `X01` برمجيًا من اكتمال بنية المصدر وصيغة المعرّف `ref` ووجود `locator` مهيكل واقتباس نصي غير فارغ ومنع الأرقام غير الموثقة في الوضع `illustrative`، لكنه **لا يتصل بالإنترنت ولا يثبت تلقائيًا مطابقة نص الاقتباس للمستند الخارجي الأصلي**؛ التحقق من دقة الاقتباس مسؤولية المراجعة الهندسية للمصدر المحفوظ محليًا.
- **عقد التوقيت الموحّد مع التعليق الصوتي (`X02`)**:
  - في ملفات الخطة (`clock: "vo"`): طول المشهد وحدوده يتحددان حصريًا من التعليق الصوتي المقاس (`plan/beats.json` + `plan/word-timings.json`).
  - يشترط `X02` وجود المشهد المستهدف وقائمة كلمات مقاسة غير فارغة في `word-timings.json`؛ ولا يمكن لأي `anchor` المرور دون كلمة مقاسة فعلية تطابقه نصًا وفهرسًا وحدودًا زمنية.
  - كل خطوة تربط `anchor: { word, text }` بنفس عقد `visual_direction.measured_words()` وتطبق قواعد `lead` / `sync` / `reveal` على شبكة `fps` المقاسة من الهوية.
  - `revealWindow` يحمل وحدة صريحة إلزامية: `unit: "vo_seconds"` في الخطة، وتتحول عبر `to_scene_local_machine` / `toSceneLocalMachine` إلى `unit: "scene_seconds"` عند الرندر المحلي للمشهد.

---

## ٤) بوابات الفحص الهندسي والتخطيط (`X01`–`X04` + `L00`–`L04`)

| الكود | ما يفحصه |
|---|---|
| `X01` | صحة بنية `sources[]`، وجود `locator` مهيكل واقتباس لكل خطوة موثقة، وحارس الوضع التوضيحي `illustrative` ومنع الأرقام غير الموثقة (فحص بنيوي محلي بدون اتصال بالإنترنت) |
| `X02` | إلزامية وجود كلمات مقاسة غير فارغة للمشهد ومطابقة كل `anchor` لـ`plan/word-timings.json`، وحدة `revealWindow` الصريحة، حدود المشهد في `plan/beats.json`، وربط `copyIds` بـ`plan/copy.json` |
| `X03` | **Occlusion Audit هندسي فعلي**: إسقاط مضلعات الأوجه ثنائية الأبعاد بترتيب الرسام `(layer, depth, seq)` وحساب نفاذية الطبقات الأمامية لكل بكسل `∏(1 - α_fg)` لكل `activeTag`، مع عتبة قابلة للضبط (`--max-occlusion` أو `qa.maxOcclusion` أو `step.maxOcclusion`، الافتراضي `0.35`) |
| `X04` | اشتقاق منطقة الأمان ديناميكيًا من `layout_p.safe_envelope()` / `layout.js:safeEnvelope()` / `layout.tsx:safeEnvelope()` (`brand.json`) وفحص كل خطوة خلال فترة نشاطها شاملة الأوجه والأسلاك وسماكات الخطوط ومسارات وجسيمات `packets` وتيارات وحبيبات `airflow` وريش الدوران `spin` ضد حدود الأمان وشريط `PLATFORM_RIGHT_RAIL` |
| `L00`–`L04` | تدقيق صناديق الإحاطة المحافظة (AABBs) بعد التفاف الأسطر والتحويلات الحركية في **P** (`layout_p.py`) و**K** (`layout.js`) و**R** (`remotion/src/lib/layout.tsx` مع `strictLayout`): `L00` صندوق غير صالح أو منطقة غير معروفة، `L01` خروج النص عن المنطقة الآمنة، `L02` تداخل نص مع نص آخر أو مع صندوق `keep` محمي (مثل حدود الرسم الهندسي)، `L03` تداخل النص مع منطقة وجه محمية `face`، و`L04` تداخل النص مع `PLATFORM_RIGHT_RAIL` (الفحص يعتمد على صناديق الإحاطة AABBs ولا يجري كشفًا مستقلًا لقصّ النص أو اقتطاعه بالبكسل) |

---

## ٥) الاستخدام السريع

```bash
# ١) توليد مسودة مبدئية لنموذج عتاد في المشروع
python3 tools/machine_explainer.py projects/my-reel --init nvme_ssd --id nvme-flow --scene 2

# ٢) فحص مستقل أو عبر reel_lint مع إمكانية تشديد عتبة الحجب
python3 tools/machine_explainer.py projects/my-reel --check --max-occlusion 0.30
python3 tools/reel_lint.py projects/my-reel
make machine-check P=projects/my-reel MAX_OCC=0.30
```
