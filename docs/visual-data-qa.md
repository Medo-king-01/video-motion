# تخطيط الصورة + وصفات البيانات + فحص الكادر

إضافات أصلية جوّه الأدوات الحالية؛ مفيش محرك جديد، ولا تثبيت Skills خارجية، ولا تغيير هوية.
P/K/R وHybrid المتتابع زي ما هم. **فحص الكادر آليًا متاح لـK فقط حاليًا**؛ وصفات البيانات لـK وR.
الخطة الدلالية مشتركة بين المحركات، لكنها قرار الوكيل وليست مولّد B-roll تلقائيًا.

## ١. اربط المعنى بالصورة قبل الكود

المشاريع الجديدة فيها `plan/visual-direction.json` بحالة `draft`. بعد قياس الـVO وحدود المشاهد:

```bash
python3 tools/visual_direction.py projects/my-reel --init --force
# --force يستبدل الخطة: استخدمه لإعادة التهيئة المقصودة فقط، مش فوق قرارات معتمدة.
```

اختار لكل beat: `presenter` (متكلم فقط)، `overlay` (رسم فوق المتكلم)، أو `cover`
(الصورة تشرح بدل المتكلم)، واكتب `why` بمعنى محدد، مش «عشان شكلها حلو».
دي معالجات جوّه المشهد، **مش** تركيب محركات فوق بعضها. الخطة لا تغيّر الصوت أو زمنه.
سجّل `status: "ready"` و`decidedBy` بعد القرار. كل مشهد مقاس لازم يظهر مرة واحدة بحدوده الأصلية.
`presenter` لا يعلن عناصر رسومية؛ `overlay/cover` لازم يعلن عناصر.

أضف `id` ثابت لكل fragment في `copy.json`. كل عنصر يحدد `kind` و`why` و`copyIds`،
ومرساة كلمة بالـindex والنص المطابق. الأرقام والـlabels والمصدر والوحدة يفضلوا نصًا موجّهًا
في `text-direction.json` بأدوار `number` و`label`، مع اختيار الخط/الحركة صراحةً.
الخطة ليست دليلًا أن التنفيذ طابق القرار؛ مراجعة الصورة والكلام ما زالت مطلوبة.

مثال مختصر (افترض beat رقم ١ من 0 إلى 3، وكلمة «سعة» مقاسة من 1 إلى 1.5):

```json
{
  "version": 1, "clock": "vo", "status": "ready", "decidedBy": "agent",
  "wordTimings": "plan/word-timings.json",
  "scenes": [{
    "scene": 1, "start": 0, "end": 3, "treatment": "cover",
    "why": "رقم واحد واضح يشرح السعة المذكورة بدل لقطة زخرفية",
    "elements": [{
      "id": "capacity", "kind": "counter", "dataset": "plan/data/capacity.json",
      "evidence": "illustrative", "why": "نفس القيمة والوحدة اللي اتقالوا في الصوت",
      "copyIds": ["capacity-number"], "anchor": {"word": 0, "text": "سعة"},
      "timing": "sync", "start": 1, "end": 2.8
    }]
  }]
}
```

الكلمات إما الملف القياسي:

```json
{"clock":"vo","scenes":[{"scene":1,"words":[{"text":"سعة","start":1,"end":1.5}]}]}
```

أو ملف قائمة نتائج `caption_align.py` الذي يحمل `index/start/final`، حيث `final` كلمات بتوقيت
محلي للمشهد. الأداة تضيف `scene.start`؛ لا تستخدم `draft` أو تخمّن word boundaries.
ضع مسار نتائج القياس داخل المشروع في `wordTimings` لتستخدمه الأداة والـlint معًا.
يمكن تمرير `--words path` لاختبار ملف بديل؛ هذا لا يغير المسار الذي يقرأه الـlint.

- `sync`: بداية العنصر عند بداية الكلمة المقاسة.
- `reveal`: لا يظهر قبل كلمة الكشف، ويستمر لنهاية الكلمة على الأقل.
- `lead`: هيكل غير معلوماتي فقط، `fact:false`، قبل الكلمة بحد أقصى ٦ إطارات عند 30fps.
  **لا يصلح** لرقم أو نتيجة/معلومة محجوبة. وصفات البيانات لا تسمح بـlead.
- كل أزمنة الخطة والكلمات القياسية **مطلقة على ساعة الـVO**. أزمنة وصفة الرسم **محلية للمشهد**:
  اطرح `beat.start` من بداية/نهاية العنصر ومن بداية/نهاية كلمة المرساة.

```bash
python3 tools/visual_direction.py projects/my-reel --check
python3 tools/reel_lint.py projects/my-reel --scan-code
```

وجود الخطة يفعّل بوابة `V01` في الـlint، والـdraft/المرساة غير المقاسة/تسريب ملف خارج المشروع
أخطاء تمنع قبوله. المشاريع القديمة التي لا تحتوي الخطة لا تتعطل تلقائيًا؛ فعّلها بـ`--init`.
الـrender المباشر لا يشغّل هذه البوابة: **لا تتخطّ مرحلة lint**.

## ٢. بيانات أصلية ووحدات صريحة

الـschema المشترك في `lib/data-recipes.js` بنسختين متطابقتين لـK وR:

```json
{
  "version": 1, "kind": "comparison", "source": "Illustrative — not a benchmark",
  "unit": "GB", "locale": "ar-EG", "decimals": 0,
  "rows": [
    {"id":"a","label":"الخيار الأول","value":16},
    {"id":"b","label":"الخيار التاني","value":32}
  ]
}
```

- `comparison`: من ٢ إلى ٨ صفوف، قيم غير سالبة، مقياس واحد يبدأ من الصفر.
- `counter`: صف واحد بقيمة غير سالبة؛ لا يظهر كرقم بلا وحدة/مصدر.
- `timeline`: من ٢ إلى ١٠٠٠ نقطة، لكل صف `at` متزايد وغير سالب؛ يقبل قيمًا سالبة.
  `at` إحداثي على محور البيانات، **مش** ثانية على فيديو التعليق. المجال الرأسي يشمل الصفر.
  الاستيفاء خطّي بين النقاط الأصلية؛ لا يختلق قياسات إضافية. الملصقات تعرض طرفي الخط فقط؛
  احرص أن وحدات المحورين واضحة في كلام/تسميات المشروع، ولا تساوِ محورين بوحدات مختلفة.
- مصدر ووحدة غير فارغين، IDs فريدة، قيم finite وفي مجال الدقة الآمن، `decimals` بين 0 و6،
  و`locale` إما `ar-EG` أو `en-US`، مع أرقام غربية 0–9 في الحالتين طبقًا للهوية. القيمة يجب ألا تحمل كسورًا أدق من الدقة المعلنة.
- الأداة تتحقق من **البنية والدقة**، مش صدق المصدر أو أن الرقم مطابق للكلام؛ دي مراجعة بشرية.
  في الخطة صنّف `evidence` كـ`user/source/illustrative` وعلّم البيانات التوضيحية على الشاشة.
  لا تستعمل البيانات الافتراضية في مثال الاختبار كأنها قياس منتج حقيقي.

```bash
# JSON: validation only؛ CSV يحتاج id,label,value (+at للخط الزمني).
python3 tools/data_recipe.py projects/my-reel/plan/data/capacity.json
python3 tools/data_recipe.py input.csv --out projects/my-reel/plan/data/capacity.json \
  --kind counter --source "Illustrative — not a benchmark" --unit GB --decimals 0
```

CSV يدعم quoted fields وBOM. ملفات الإخراج الجديدة فقط، بلا overwrite أو symlink.
لا تنزيل بيانات، ولا إرسال صوت، ولا API مدفوع. الـJSON الناتج لا يضيف نفسه إلى الكود تلقائيًا.
في K ضع البيانات في module محلي أو داخل `assets/` واقرأها أثناء `init`، وفي R import JSON محلي.
**لا** تتوقع أن خادم K يقدّم أي ملف عشوائي من `plan/`.

### الرسم داخل محركاتنا

```js
// K: spec.data = ملف البيانات؛ spec.start/end/anchor أزمنة محلية مقاسة.
import {drawDataRecipe} from '../lib/data-visual.js';
drawDataRecipe(ctx, spec, localSeconds, {
  direction, scene: 1, id: 'capacity', x: 140, y: 400, w: 800, h: 600,
});
```

```tsx
// R: لا مؤقت جديد؛ مرّر نفس ساعة الإطار المحلية المستخدمة في المشهد.
import {DataRecipe} from './lib/DataRecipe';
<DataRecipe spec={spec} time={localSeconds} direction={direction}
  scene={1} id="capacity" x={140} y={400} width={800} height={600}/>
```

`spec = {data, start, end, anchor:{text,start,end}}`. الحقائق/القيم مخفية قبل `anchor.start`،
تتحرك بـeasing الأصلي خلال الكلمة، وتستقر على القيمة الصحيحة عند `anchor.end` ثم تثبت
حتى نهاية العنصر. الوحدة والمصدر والهيكل غير المعلوماتي قد يظهروا من `spec.start`.
التقدّم دالة نقية في الوقت؛ seek للخلف أو إعادة إطار لا يغير الناتج. النص كله whole-word RTL،
الوحدة والمصدر يستخدما `label` والقيم `number`؛ IDs الفرعية مثل `capacity.unit/source/value`
و`capacity.<row-id>.label/value` متاحة للاختيارات الفردية.
هذه primitives تنفيذية، مش بديل للدَّرْو من مكتبة الحركات أو تصريح لإضافة حركة غير مختارة.
التصميم الحالي light-theme وبألوان الهوية فقط؛ K وR يشتركان في الأرقام والتوقيت، مش ضمان تطابق البكسلات.

## ٣. فحص الكادر في K

```bash
node tools/layout_audit.mjs --project projects/my-reel \
  --out projects/my-reel/cache/layout-v1
# تجربة سريعة فقط؛ لا تسمّها اعتمادًا شاملًا:
node tools/layout_audit.mjs --project projects/my-reel \
  --out projects/my-reel/cache/layout-sampled --from 0 --to 3 --every 6
```

استخدم مجلد إخراج جديد. القالب الجديد مطلوب: المشروع القديم عنده نسخته من `src/`،
فمش بيتحدث تلقائيًا بتعديل المكتبة. راجع/انقل instrumentation مع الحفاظ على كود مشاهده.
الفحص يستخدم Chromium الحالي، بلا FFmpeg أو محرك جديد، ويمنع requests خارج الخادم المحلي.
فشل تحميل resource/font، أو غياب capture contract، لا يُعلَن PASS.

الالتقاط يلفّ `fillText/strokeText` على سياق الكانفس الرئيسي فقط، ويستخدم `TextMetrics` الحقيقية
والـtransform الحالي ويحوّل الإحداثيات إلى 1080×1920. stroke/fill المتطابقان يُحسبان عنصرًا واحدًا.
`drawDirectedText` و`drawWordCaption` يسجلان النص/الـID والمنطقة تلقائيًا.
النص غير الموجّه يُلتقط أيضًا، لكنه يظل مخالفًا لعقد النص وT04.

| كود | المعنى |
|---|---|
| L00 | تسجيل box ناقص/غير صالح أو منطقة نص غير معروفة |
| L01 | ink خارج منطقة النص المحددة وهوامش الهوية |
| L02 | تداخل ink نصين أو نص مع منطقة محمية، بحد أدنى 2px على المحورين |
| L03 | نص يغطي منطقة وجه مسجلة، حتى لو النص كله داخلها |

محتوى: y200–1350، كابشن: y1350–1500، HUD: y0–200، والهامش الأفقي 40px.
النص المباشر يُحسب content، ويمكن تسجيل HUD مقصود بـ`withLayout(ctx,{id,zone:'hud'},draw)`.
الكابشن في موضع خارج نطاقه يظهر كخطأ؛ أصلح موضعه بدل توسيع المنطقة.

لحماية الوجه، قِس المستطيل في **كل pose** وسجّله في خيار presenter:

```js
drawPresenter(ctx, pose, localSeconds, {faceBox: {x: /* fraction */, y: /* fraction */, w: /* fraction */, h: /* fraction */}});
// المستطيل كسور داخل الصورة الأصلية [0..1]؛ استخدم قياسًا فعليًا، مش تخمينًا من حجم الصورة.
```

`drawPresenter` يحوّل المستطيل مع نفس scale/tilt/bob. غياب القياس يسجل L00 بدل اختراع وجه آمن.
`PoseTrack` و`drawPoseBlend` يقبلان `faceBoxes: {poseSlug: measuredBox}` لحماية كل وضعية بقياسها أثناء الانتقال؛
لا تمرّر مستطيلًا واحدًا لوضعيات مختلفة. `protectBox` متاح للصور/المناطق الخاصة التي يرسمها كودك؛ لا يوجد كشف وجوه بصري تلقائي.
ملف poses الحالي **ليس** قياسًا للوجوه، فلا تدّع اعتماد فحص الوجه لكل المكتبة.

`report.json` يسجل `pass/fail/incomplete`، النطاق والـstride، والإطار/الثانية والـIDs والـboxes
والأخطاء. حتى ١٢ صورة للكادرات المخالفة عليها حدود حمراء للـboxes المسؤولة. غياب أي نص
طوال النطاق = incomplete، مش نجاح. exit غير صفر للفشل/incomplete أو أي فشل تشغيل.
التقرير النهائي لا يُكتب لو المتصفح تعطل مبكرًا: غياب التقرير **ليس** اعتمادًا.

**الحدود:** AABB محافظة وليست pixel segmentation، فتقدر تبلغ عن نص مخفي خلف clip/occlusion؛
ولا تشمل ظل/blur/stroke extents بدقة، أو raster/offscreen text، أو كل الرسومات غير النصية.
لا تثبت جودة التباين، القراءة على الموبايل، جمال التكوين أو صدق البيانات. `--every >1` ممكن يفوّت
تصادمًا سريعًا؛ الاعتماد الافتراضي كل إطار 30fps، ومعه مراجعة بصرية وسماع الصوت الفعلي.

### فحص إضافي: ثبات الإطار عند الرجوع

أضف `--replay` لنفس أمر audit: يقارن RGBA الفعلية وبيانات التخطيط عند إعادة الإطارات بالعكس.
`R01` اختلاف بكسلات، و`R02` اختلاف snapshot؛ الفشل يمنع PASS، وغياب الطلب يسجل `not-requested`.
هذا ليس فحص loop seam أو ضمانًا عبر المتصفحات. [شرح الاستمرارية والفحص وحدودهما](charlie-motion-review.md).

## ٤. إعادة إنتاج الأدلة

```bash
python3 tools/visual_verify.py --out .cache/my-visual-proof --remotion
python3 -m pytest tests/test_visual_tools.py -q
```

ينتج ٣ وصفات K و٣ صور R مع typecheck، و`K-recipes.png` و`R-recipes.png` للمراجعة،
و`audit-pass/report.json` (١٨٠ إطارًا)، و`audit-fail/` بتصادمات مصطنعة وصور معلَّمة.
الـFAIL في الحالة المصطنعة **متوقع ومؤكد**، مش فشل verification.
الأمثلة بيانات وتوقيت **اختباريان**، ليست فيديو تسليم بلا صوت ولا دليل تزامن مع تسجيل حقيقي.
للاستخدام الإنتاجي لازم الكلمات المقاسة من الـVO الأصلي. لا تدخل مخرجات الكاش في Git.
`--remotion` يشغّل `npm ci` من lockfile القالب؛ هناك تحذير Zod version mismatch حالي
بسبب الـoverride الموجود أصلًا، لكن typecheck والرندر مُختبَران. لم نغيّر الاعتماديات أو نتراجع عن الـoverride.
