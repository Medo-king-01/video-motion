# Motion المرحلة الثانية — فيزياء وحالات للرندر

اختيار المستخدم: إضافات الرندر، **من غير واجهة تأليف تفاعلية**. التنفيذ أصلي داخل الاستوديو، وليس تثبيتًا لـMotion أو ضمان توافق مع كل APIs الخاصة به. الحالة الكاملة للـ44 اختيارًا في [خطة التنفيذ](motion-rollout.md) و[`rollout.json`](../medo-motion/motion/rollout.json).

## الملفات والوحدات

- K: `src/lib/motion-state.js`، ومن داخل `src/scenes/` استورده من `../lib/motion-state.js`.
- R: `src/lib/motion-state.js`، بنفس مصدر K حرفيًا، ويُستدعى بزمن `useCurrentFrame()/fps` المحلي للمشهد.
- P: `motion_state.py`، ويستخدم أسماء snake_case: `spring_state`, `duration_spring`, `compile_inertia`, `compile_retarget`, `compile_follow`, `compile_variants`, `compile_values`.

كل الأزمنة **ثوانٍ**، والسرعة وحدات/ثانية. إذا كانت مرساة VO مطلقة، اطرح بداية المشهد أولًا. لا ساعة حائط أو live callbacks أو subscriptions أو integration تتراكم من frame لآخر. الخطط JSON، والعينات ناتجة من الزمن مباشرة. لا تغيير تلقائي للـVO أو طول الفيلم.

هذه samplers للهندسة والحالة، **وليست بوابات للحقائق**. الرقم أو النص الذي يصل إليه sampler قبل الكلام لا يجوز عرضه كحقيقة قبل المرساة المقاسة. احتفظ بخطة visual-direction وdirected text والهوية ومراجعة الكادر.

## 01 — نابض مضبوط بالمدة

```js
import {springState, durationSpring} from '../lib/motion-state.js';
const physical = springState(140, 800, t, {
  stiffness: 170, damping: 18, mass: 1, velocity: 0,
});
const finite = durationSpring(140, 800, t, {
  duration: 0.7, bounce: 0.35, velocity: 0,
});
// {value, velocity}
```

`springState` حل تحليلي للمعادلة `m*x'' + c*x' + k*(x-target) = 0` في الحالات under/critical/over-damped. يقبل stiffness وmass موجبين وdamping غير سالب؛ لا توجد محاكاة تعتمد على fps. زمن سالب يرجع البداية بسرعة صفر؛ عند الصفر تُحفظ السرعة الابتدائية المعطاة. النابض الحر لا يُقصّ إلى target تلقائيًا.

`durationSpring` يضبط damping ratio من `1-bounce` وfrequency من `8/(ratio*duration)`، ثم يضيف تصحيح Hermite للنهاية. عند `duration` يصل إلى الهدف **بالضبط وبسرعة صفر**، مع الحفاظ على القيمة والسرعة الابتدائيتين. النهاية C1؛ التسارع ليس مضمون الاستمرارية. هذا **هبوط إخراجي محدود** وليس ادعاء أن نابضًا حرًا يستقر في وقت منتهٍ، أو أن bounce يطابق تعريف Motion رقميًا.

`bounce` بين 0 و0.8؛ duration موجب. conditioning المدعوم: natural frequency بين `1e-6` و`1e6` وdamping ratio حتى `1e4`. النتائج غير المحدودة تُرفض. الـovershoot لا يعني سماحًا بالخروج من safe zone؛ اختيار إزاحة مناسبة مسؤولية التكوين.

## 02 — Inertia مع bounds وsnap

```js
import {compileInertia} from '../lib/motion-state.js';
const slide = compileInertia({
  from: 180, velocity: 1700, timeConstant: 0.28,
  decayDuration: 0.75, settleDuration: 0.35,
  min: 140, max: 940, snap: [260, 540, 820],
});
const {value, velocity, target, done} = slide.at(t);
// slide.duration = decayDuration + settleDuration
```

المرحلة الأولى decay تحليلي: `from + velocity*tau*(1-exp(-t/tau))`. الهدف المتوقع `from + velocity*tau` يُحصر بالحدود أولًا، ثم يُختار أقرب snap point؛ التعادل يختار الأصغر، مستقلًا عن ترتيب القائمة. نقاط snap غير الخالية يجب أن تكون أرقامًا داخل الحدود.

بعد `decayDuration` يبدأ هبوط finite spring حرج من آخر موضع وسرعة إلى الهدف، وينتهي بعد `settleDuration` بسرعة صفر. من دون اصدام بحد، الموضع والسرعة مستمران عند تسليم المرحلتين. بعد النهاية تُحفظ النتيجة النهائية، حتى عند طلب إطار بعيد جدًا.

**الحدود hard clamps، وليست bounce physics.** الاصطدام قد يقطع السرعة إلى صفر؛ لا ندعي C1 عند الاصطدام. لا خروج عن min/max، والبداية يجب أن تكون داخلهما. لا snapping عشوائي أو callback لتعديل الهدف. لا تضف `slide.duration` تلقائيًا إلى مدة الفيلم؛ نافذة الحركة يجب أن تتسع داخل المشهد المقاس.

## 03/04 — Retarget وfollow من سجل أحداث

```js
import {compileRetarget, compileFollow} from '../lib/motion-state.js';
const log = {
  version: 1, initial: 180, velocity: 0,
  physics: {stiffness: 170, damping: 18, mass: 1},
  events: [
    {at: measuredLocalOnset, target: 820},
    {at: measuredNextOnset, target: 340},
  ],
};
const retarget = compileRetarget(log);
const follow = compileFollow({...log, lag: 0.14});
const state = retarget.at(t); // {value, velocity, target}
```

الأحداث **مرتبة تصاعديًا بشكل صارم**، غير سالبة، ولا يُسمح بهدفين في اللحظة نفسها. يُحسب الموضع والسرعة عند كل حدث أثناء compile، وتبدأ القطعة التالية منهما. تغيير الهدف لا يعيد السرعة للصفر ولا يجعل النتيجة معتمدة على آخر frame طُلب. تعديل سجل الإدخال بعد compile لا يغيّر الخطة.

الـfollow هنا نابض يتتبع **هدفًا scalar ثابتًا بين الأحداث**. lag يؤخر أوقات أحداث الهدف فقط، ولا يسجل pointer أو يُستنتج من حركة المستخدم. لا مستقبل يؤثر قبل وقته. لو كانت velocity الابتدائية غير صفرية، تبدأ الحركة نحو initial من الصفر الزمني حتى أول حدث؛ lag لا يوقفها.

المخرجات scalar؛ للمحورين أنشئ sampler لكل محور. لا يدّعي هذا التنفيذ تتبع مسار مستمر اعتباطي أو live generators. الـretarget الحر لا يفرض تسكينًا مصطنعًا عند نهاية المشهد؛ خطط الهدف/التوقيت بما يحافظ على نهاية مناسبة.

## 08 — Variants هرمية داخل الفيلم

```js
import {compileVariants} from '../lib/motion-state.js';
const scene = compileVariants({
  version: 1,
  root: {
    id: 'panel', initial: 'off',
    variants: {off: {y: 20}, on: {y: 0}},
    children: [
      {id: 'card', variants: {off: {x: 140}, on: {x: 620}}},
    ],
  },
  events: [
    {at: measuredLocalOnset, label: 'on', duration: 0.3,
     order: 'beforeChildren', stagger: 0.08, easing: 'cubicOut'},
  ],
});
const states = scene.at(t); // {panel:{y:...}, card:{x:...}}
```

الطفل يرث **اسم** initial إن لم يحدده. كل node له جدول قيمه الخاص؛ كل event label ينتشر إلى كل الشجرة، ويجب أن يكون موجودًا عند كل node. الـstates كائنات متطابقة البنية من القيم التي يقبلها mixValue؛ ليست partial CSS patches أو وظائف تُنفذ لكل frame. IDs فريدة. الحد 256 node وعمق 32.

- `together`: الأب والأبناء يبدأون من نفس الأساس، ثم stagger بين الأشقاء.
- `beforeChildren`: الأب أولًا ثم الأبناء، مع stagger بين الأشقاء.
- `afterChildren`: الأب ينتظر نهاية كل الأبناء، ثم يتحرك.

النمط يطبق تكراريًا في مستويات الشجرة؛ duration واحدة لكل node في الحدث. الحدث التالي يجب أن ينتظر **كل** انتقال الحدث السابق. tolerance قدرها `1e-12` ثانية تمنع خطأ التداخل الكاذب عند حدود الكسور؛ ليست سماحًا بتداخل إطارات. لا مقاطعة variants أثناء انتقال سابق في هذه النسخة، ولا تلقائية DOM inheritance أو gestural states. بدون events ترجع initial ثابتة. العينات كائنات جديدة لا تغيّر الخطة.

## 11 — Value graph مشتق من الزمن

```js
import {compileValues} from '../lib/motion-state.js';
const values = compileValues({
  version: 1,
  sequence: {
    version: 1,
    clips: [{id:'x',track:'x',at:measuredLocalOnset,duration:0.6,from:140,to:620}],
  },
  constants: {factor: 2},
  nodes: [
    {id:'p',op:'map',input:'x',range:[140,620],output:[0,1]},
    {id:'width',op:'mix',input:'p',from:140,to:420},
    {id:'twice',op:'multiply',inputs:['x','factor']},
    {id:'sum',op:'add',inputs:['x','twice']},
    {id:'speed',op:'velocity',input:'x',step:0.001},
    {id:'transform',op:'template',digits:3,parts:['translateX(',{input:'x'},'px)']},
  ],
});
const computed = values.at(t);
```

الـsequence من compiler المرحلة الأولى، وconstants اختيارية. النتيجة تحتوي المصادر والعقد المشتقة. يسمح بترتيب تعريف غير topological، لكنه يرفض cycles وmissing references وduplicate IDs قبل الرندر. الحد 128 عقدة. لا `eval` أو JS functions داخل JSON، ولا شراء أو اتصال خدمة.

- `map`: مجال من رقمين مختلفين إلى طرفين متطابقي البنية؛ clamp افتراضي true، و`clamp:false` يسمح بالاستقراء صراحةً.
- `mix`: يخلط from/to بقيمة input رقمية، ضمن حدود mixValue: لا مزج ألوان اعتباطي أو تحويل وحدات.
- `add` / `multiply`: مصادر رقمية غير خالية.
- `velocity`: **تقدير** مركزي `(value(t+h)-value(t-h))/(2*h)`، بخطوة ثابتة بالثواني وليست fps. الافتراضي `1/600`، ومجاله أكبر من صفر وحتى ثانية. عند cut أو easing boundary قد ينتج متوسطًا حول الانقطاع، وليس سرعة فيزيائية دقيقة. لا derivatives متداخلة؛ استخدم velocity التحليلية من physics sampler للفيزياء.
- `template`: strings ومراجع scalar فقط. digits من 0 إلى 6، والافتراضي 3؛ التقريب half-away-from-zero على قيمة float، مع إزالة أصفار النهاية. للأرقام الأصغر مطلقًا من `1e21`. هذه صياغة نصية، **وليست parser أو تطبيقًا آليًا لـCSS/HTML**. لا تستخدمها لطباعة نص عربي بدل directed helpers أو لكسر بوابة الحقائق.

## التحقق

```bash
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 -m pytest tests/test_motion_state.py -q
python3 tools/visual_verify.py --out cache/new-state-proof --states --replay --remotion
bash tools/ci.sh
python3 tools/selftest.py --remotion --hybrid
```

شغّل CI وselftest بالتتابع، لأن كليهما يشغّل اختبارات تستخدم أسماء مشاريع مؤقتة مشتركة. Fixture الجديدة اختبارية بلا VO: K clip صامت 2.4 ثانية، و72 إطارًا مع replay، وK/R stills ومراجعة TypeScript. P مُتحقق رياضيًا بالمقارنة؛ لا ندّعي proof مرئي P لهذه الوصفات الجديدة. فحص replay داخل نفس المتصفح والتشغيل، لا ضمان لكل الأجهزة.
