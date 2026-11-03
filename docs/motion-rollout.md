# خطة تنفيذ Motion: مميزات الرندر من غير واجهة تأليف

**قرار المستخدم:** اختيار المميزات، باستثناء واجهة التأليف التفاعلية بسبب تكلفتها وحجم العمل.
التنفيذ مرحلي، **وليس إعلانًا أن كل الـ44 اختيارًا اكتمل**. الحالة القابلة للتتبع في
[`../medo-motion/motion/rollout.json`](../medo-motion/motion/rollout.json)، بأرقام المراجعة السابقة نفسها.

## حدود القرار

- لا محرر بصري جديد، لا drag/scroll authoring، لا pointer recording أو live viewport events.
- إعادة ترتيب القوائم **داخل الفيلم** تظل ضمن الخطة؛ المستبعد هو واجهة السحب لإعادة التأليف.
- الـtimeline البرمجي والعلامات داخل ملفات المشروع مطلوبان؛ المستبعد هو واجهة تحريره الحية.
- كل توقيت إنتاجي من VO المقاس؛ لا نغير الصوت أو الهوية أو طول الفيديو، ولا نعمل loop للمشهد كله.
- لا تثبيت Motion runtime أو محرك جديد. التطبيقات الحالية أصلية على الرياضيات الموجودة في الاستوديو.
- Three متاح اختياريًا بنطاق K/R محدود بعد دراسة مستقلة؛ vgpu ما زال مخططًا. لا اعتماد Three افتراضيًا، ولا افتراض GPU عتادي.
- Motion+ وكل المكونات المدفوعة مستبعدة صراحةً؛ لا شراء ولا نقل كود مدفوع. تظل مراجعة رخص الاعتماديات المجانية مطلوبة.
  Motion Studio الخارجي وMCP/AI authoring خارج النطاق المستبعد أصلًا.

## المرحلة الأولى — المنفذ فعليًا

نموذج جديد: K `lib/motion-plan.js`، ونسخة مطابقة في R؛ Python `motion_plan.py` لـP.
لا wall clock أو callbacks زمنية أو subscriptions حية أو randomness. نفس spec ونفس الزمن يعطيان
نفس القيم، بغض النظر عن ترتيب أخذ العينات. اختبارات parity تقارن Python وJavaScript.

| أرقام المراجعة | التنفيذ الحالي | ما لا ندّعيه |
|---|---|---|
| 05 | `staggerTime` / `stagger_time`: first/last/center/edges/origin رقمي، مع easing للتوزيع | لا يفكك حروف العربي ولا يختار حركته بدل الوكيل |
| 06 | `compileSequence` / `compile_sequence`: markers، offsets، بداية/نهاية clip سابقة، tracks مستقلة | العلامة ليست قياسًا للصوت بذاتها؛ المؤلف يربطها بالـVO الحقيقي |
| 09 | `cycleValue` / `cycle_value`: تكرار **محدود**، loop/reverse/mirror وتأخير بين الدورات | لا infinite loops، ولا reset للتعليق أو المشهد |
| 10 | timing/easing مستقل لكل property عبر clips على tracks منفصلة | لا تغيير للـVO أو تحريك حقائق قبل مرساتها |
| 20 | `arcAt` / `arc_at`: قوس بارتفاع بالبكسل واتجاه tangent | لا ضمان تلقائي أن المسار داخل safe zones؛ راجع الكادر |
| 07 جزئي | compiler رأسه بيانات ولا يعتمد على UI | nesting محدود أضيف في المرحلة الخامسة؛ live editing مستبعد |
| 12 جزئي | `mixValue` / `mix_value`: أرقام ومصفوفات وobjects متطابقة البنية، وpx/%/deg بوحدات متطابقة | لا تحويل وحدات، لا CSS parser عام أو custom morph mixer، ولا مزج ألوان خارج الهوية |
| 17 جزئي | `presenceAt` / `presence_at`: enter/hold/exit داخل نافذة ثابتة | هذه الدالة منفردة؛ دعم المجموعة المضاف لاحقًا موصوف في المرحلة الثالثة |
| 21 جزئي | `pathAt` / `path_at`: خط أو Bezier من 2–4 نقاط، مع tangent | الدالة نفسها لا تقرأ SVG؛ يوجد compiler محدود لاحقًا، وليس normalization لمسارات اعتباطية |

## المرحلة الثانية — الفيزياء والحالات

تم تنفيذ 01–04 و08 و11 في `motion-state.js` (K/R) و`motion_state.py` (P):
نابض تحليلي ونابض ذو هبوط محدود بالمدة، inertia بحدود صلبة وsnap، retarget يحافظ على الموضع والسرعة،
follow scalar من سجل أحداث، variants هرمية وvalue graph مشتق من الزمن. لا live inputs أو واجهة تأليف.

[الاستخدام الكامل والمعادلات والحدود والاختبارات](motion-state.md).
«مكتمل» هنا **داخل النطاق الأصلي المحدد للرندر offline**؛ لا يعني كل API من Motion أو physics ارتداد عند الحدود،
أو تتبع هدف مستمر اعتباطي، أو مقاطعة انتقال variants. المتبقي خارج المرحلة الحالية لم يتحول إلى مكتمل.

## المرحلة الثالثة — التخطيط والعناصر

إضافة snapshots هندسية حتمية ومجموعات بIDs مستقرة، إعادة ترتيب مؤلَّفة، حالات sync/wait/popLayout،
قياس خطوط حقيقي لـCanvas وHarfBuzz، ورسم/مسح مسار متعدد النقاط وmorph لحلقة واحدة وbindings محددة النوع.
[التفاصيل والأمثلة وحدود التنفيذ](motion-geometry.md). أغلب هذه الأرقام جزئي: ليست snapshots DOM آلية،
ولا تصحيح transforms عامة، ولا SVG اعتباطي بثقوب، ولا ربط CSS شامل. لا محرر تفاعلي ولا تغيير لمدد VO.

## المرحلة الرابعة — رندر وبنية جزئية وSVG مستقر محدود

سياسة اختيارية للقيم الزخرفية قليلة الحركة، حساب sampler مرة لكل إطار، scope صريح لتنظيف الموارد،
وقياس محلي لزمن تقييم إطارات K، مع typed SVG adapter. [الاستعمال والقيود](motion-render.md).
[SVG](motion-svg.md) يجمّع المسارات والأشكال الثابتة إلى هندسة موحدة P/K/R؛ يرفض الخصائص غير المدعومة.
لا SVG DOM/CSS عامة، ولا morph تلقائي للثقوب، ولا profiler لـGPU، ولا إدارة موارد أو تقليل حركة شامل تلقائي.

## المرحلة الخامسة — التسلسل المتداخل وmorph متعدد الحلقات

`compileNestedSequence` / `compile_nested_sequence` لتسلسلات محلية بعلامات وtracks متداخلة،
و`compileSvgMorph` / `compile_svg_morph` لمضاهاة حلقات SVG المغلقة المؤلَّفة مع فحص محافظ للتقاطعات على الانتقال.
[الاستخدام والقيود](motion-nested-morph.md). لا يتحول ذلك إلى SVG شامل، ولا morph عند اختلاف topology،
ولا يغني عن فحص العربية والـVO؛ لا محرر ولا تغيير تلقائي للمدة.

## المرحلة السادسة — تكامل اختياري في P/K/R/Hybrid

وضع `normal` هو الافتراضي، و`reduced` صريح ومحدود بعناصر زخرفية مؤلَّفة، مع فصل كاش P حسب الوضع.
حينها أتاح K scopes لكل مشهد وP تهيئة وتنظيف الموارد لكل chunk أو segment؛ أضيف لاحقًا scope متزامن لمكوّنات R.
القياس الاختياري يغطي capture/write وflush في K، وrender/write وflush لـP segment، وwall لـR/Hybrid،
ولا يقدّم قياس GPU. [التعليمات والحدود](motion-render.md). ما زالت 32 و36–38 جزئية،
وليست شهادة إتاحة أو تكاملًا تلقائيًا لكل المشاهد. لا تغيير لمدة الفيلم أو توقيت VO.

## المرحلة السابعة — جدوى 3D وفحص البيئة

أداة محلية اختيارية تفحص WebGL2 وWebGPU بأسئلة محدودة عن التنفيذ، مع مراجعة أولية للرخص والتكلفة،
من غير تنزيل Three أو vgpu أو Motion. WebGL2 في بيئة الاختبار كان برمجيًا؛ WebGPU بلا adapter.
[نتائج الفحص والبدائل وحدودها](motion-gpu-feasibility.md). وقت المرحلة السابعة بقيت 39 و40 planned، و43 تحتاج مراجعة
وترخيصًا ملائمًا قبل الاعتماد أو الشراء؛ نجاح فحص API لا يثبت تسريعًا فعليًا أو جاهزية الدمج.

## المرحلة الثامنة — طبقة Three محدودة اختيارية في K

جسر WebGL2 من Three r187 إلى Canvas 2D في K، بقيَم متزامنة مشتقة من زمن المشهد، وrenderer داخل scope
مع مسؤولية صريحة لأصول المشهد. الحزمة MIT مقفلة للاختبار الاختياري وليست جزءًا من الإعداد الافتراضي؛
رُندر المشهد الاصطناعي داخل K وHybrid على تنفيذ برمجي فقط. [الاستخدام وحدود الدعم](motion-three.md).
في تلك المرحلة بقيت 39 **partial** ولم يكن جسر Three لـR متاحًا بعد؛ 40 تبقى planned. Motion+ مستبعد الآن.

## المرحلة التاسعة — طبقة Three اختيارية محدودة في R

`ThreeCanvas` يستخدم الجسر نفسه في R وscope تنظيف متزامن بترتيب LIFO، مع زمن محلي يمرره المؤلف
وتحرير أصول المشهد المملوكة له صراحةً. Three ليس اعتمادًا افتراضيًا؛ انظر [العقد والتحقق](motion-three.md).
39 تبقى **partial** لجسر Three في K/R؛ 40 **planned**. يوجد 3D برمجي أصلي منفصل في P/K، لا جسر Three في P ولا vgpu أو إثبات GPU عتادي.
الاختبارات الاصطناعية تشمل نصًا عربيًا بمرساة اختبارية ثابتة في الوضعين، لا VO إنتاجيًا.


## المرحلة العاشرة — نوافذ SVG مستقلة للخطوط

تحكم مؤلف ومحدد بـstart/end/offset لكل contour في P/K/R، مع رفض النوافذ غير الصالحة
والحفاظ على مسار `progress` السابق. التعبئة ثابتة، ولا تُضاف ميزات SVG العامة أو توقيتات VO تلقائية.
[الاستخدام والتفاصيل](motion-svg.md). 22 تبقى **partial**، وليست SVG dash/markers كاملة.

## الجولة الأخيرة — توسيع مجاني واختبارات إضافية

دعم inline style ثابت وتدرجات محلية خطية ودائرية وopacity للشكل في SVG ضمن حدود صريحة، وtimeScale للتسلسلات المتداخلة، وربط IDs صريح واحد لواحد
بين مجموعتين، وأشجار رقمية مؤلَّفة لوضع reduced، و`useScopedEffect` لموارد R المتزامنة.
صُحح اتجاه وجه المكعب الأيسر في 3D البرمجي الموجود في P/K واختُبر seek عكسي في P. أضيف تلاشي بين أصول SVG غير المتوافقة (لا morph هندسي) ورسم بياني صريح لتجميع حسابات الإطار. فحص WAAPI
المحلي نجح يدويًا؛ WebGPU لم يجد adapter في بيئة الاختبار، ولم يُنفذ vgpu أو يُثبت تسريع عتادي.
Motion+ مستبعد؛ لا شراء. تبقى الميزات المذكورة جزئية بحدود موثقة، ولا إعلان SVG عام أو إتاحة معتمدة.

## استخدام sequence

```js
import {compileSequence, arcAt, staggerTime} from '../lib/motion-plan.js';
const sequence = compileSequence({
  version: 1,
  markers: {spokenWord: measuredLocalOnset},
  clips: [
    {id:'card-x', track:'card.x', at:'spokenWord', duration:0.4,
     from:140, to:620, easing:'cubicInOut'},
    {id:'card-opacity', track:'card.opacity', at:'<', duration:0.2,
     from:0, to:1, easing:'linear'},
    {id:'detail-y', track:'detail.y', at:{label:'spokenWord',offset:0.5},
     duration:0.3, from:700, to:800, easing:'easeOut'},
  ],
});
const values = sequence.at(sceneLocalSeconds);
```

- الاستيراد من مشهد K في `src/scenes/`؛ في R استخدم مسار `./lib/motion-plan.js` المناسب للمكوّن.
- Python: `from motion_plan import compile_sequence, arc_at, stagger_time`، ثم `sequence.at(t)` بنفس JSON.
- كل التوقيتات **ثواني محلية للمشهد**. اطرح `beat.start` من الـVO المطلق قبل بناء markers.
- `at` رقم، أو اسم marker، أو `{label,offset}`، أو `<` لبداية clip السابقة، أو `>` لنهايتها.
  «السابقة» هنا ترتيب clips في الملف، مش آخر إطار مرسوم.
- IDs فريدة، track اسم خاصية؛ clips على track نفسها لا تتداخل. ترتيبها يُحسم أثناء compile.
- تتطلب استمرارية from/to بين clips على نفس track، إلا لو `cut:true` مقصود. لا إعادة start صامتة.
- قبل أول clip تُعاد `from`، وفي الفجوة تُحفظ نتيجة clip السابقة، وبعد الأخيرة تُحفظ `to`.
  **ده sampler هندسة، مش بوابة حقيقة**؛ قيم الأرقام/copy الفعلية لازم تظل تحت مرساة الكلام وخطة visual-direction.
- `duration` المحسوبة هي نهاية آخر clip، مش إذن لتغيير مدة الفيديو. المؤلف يضمن أنها داخل beat المقاس.
- الـcompiler يحتفظ بنسخة من المدخلات، والعينات لا تسمح بتعديل الحالة الداخلية عن طريق المخرجات.
- لا unit conversion من `%` إلى px؛ كل adapter يحوّل حسب مرجعه صراحةً. لا تساوي strings مجردة أو ألوانًا مختلفة.

## Stagger والدورات

```js
const start = staggerTime(index, count, {
  start: measuredStart, each: 0.08, from: 'center', easing: 'easeInOut',
});
const {value, active, done} = cycleValue(0.95, 1.05, t, {
  start: 0.4, duration: 0.5, repeat: 1, repeatDelay: 0.1,
  type: 'reverse', easing: 'cubicInOut',
});
```

`repeat` عدد الإعادات بعد التشغيل الأول. delay يحفظ نهاية الدورة السابقة.
`reverse` يرجع على نفس منحنى الزمن، و`mirror` يبدّل الطرفين ويشغل المنحنى للأمام؛ يختلفان مع easing غير متماثل.
النهاية ثابتة بعد آخر دورة. `active` للنافذة فقط، وليس ترخيصًا لإظهار معلومة قبل الكلام.
تحمّل نهايات الكسور الزمنية يستخدم tolerance صغيرة جدًا عند 0/1، مش انزياح إطار.

## المسارات والظهور

```js
const point = arcAt({x:180,y:1000}, {x:900,y:1000}, progress, -180);
// point.x/y/angle؛ ارتفاع القوس -180 يعني المنتصف أعلى من خط الطرفين بـ180px.
const curve = pathAt([{x:100,y:900},{x:400,y:400},{x:850,y:950}], progress);
const presence = presenceAt(t, {start:0,enterEnd:0.2,exitStart:1.6,end:1.8});
```

نقطة البداية والنهاية والمسارات يجب أن تبقى داخل التكوين المعتمد؛ زاوية tangent اختيار للرسم،
مش تطبيق دوران تلقائي على النص. زمن `end` هو نهاية الظهور فعلًا؛ لا تمديد للمشهد لانتظار exit callback.
الـpresence لا تختار opacity حركة النص: استخدم directed helpers وخطة الخط/الحركة كالمعتاد.

## تحقق قابل للإعادة

```bash
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 -m pytest tests/test_motion_plan.py -q
python3 tools/visual_verify.py --out cache/new-plan-proof --plans --replay --remotion
bash tools/ci.sh
python3 tools/selftest.py --remotion --hybrid
```

المعاينة بيانات/توقيت اختباريان، مش VO حقيقي أو فيديو تسليم. تنتج لقطات K/R، وK clip صامت 1.8s،
وفحص layout + reverse-seek لـ54 إطارًا. الرندر الجديد مُتحقق في K/R؛ Python هنا مُتحقق حسابيًا بالمقارنة،
ولا ندّعي لقطة P جديدة لهذه الوصفات. مخرجات الكاش لا تدخل Git.

## ترتيب المتبقي

1. **حدود الرندر والبنية:** استكمال 32 و36–38 و41 خارج التكامل الجزئي الحالي حسب الحاجة والتحقق.
2. **الاعتماديات الخاصة:** 39 تكامل Three محدود، و40 دعم vgpu مخطط؛ 43 مستبعد للمدفوعات؛ 35 فحص WAAPI محلي فقط دون تسريع أو دمج تلقائي.

تبقى حدود التخطيط الجزئية وSVG وbindings العامة للتقييم لاحقًا. الملف machine-readable يحفظ الحالة لكل رقم، بما فيها المميزات الجزئية والمستبعدة؛ لا تُعامل planned على أنها جاهزة.
