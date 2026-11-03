# المرحلة الخامسة: تسلسلات متداخلة وSVG morph متعدد الحلقات

التنفيذ أصلي بلا Motion runtime أو واجهة تأليف. كل عينة تعتمد على زمن المشهد الصريح لا على الإطار السابق، ولا يمدد الفيديو أو يغير الصوت. يستعمل P وK/R البيانات نفسها؛ نسختا JavaScript متطابقتان.

## تسلسل داخل تسلسل

```js
import {compileNestedSequence} from '../lib/motion-plan.js';
const plan = compileNestedSequence({version:1, markers:{word:0.4}, items:[
  {id:'panel', at:'word', sequence:{version:1, markers:{go:0.1}, items:[
    {id:'move', track:'x', at:'go', duration:0.5, from:100, to:500, easing:'cubicInOut'},
    {id:'detail', at:'>', sequence:{version:1, items:[
      {id:'appear', track:'opacity', at:0, duration:0.2, from:0, to:1},
    ]}},
  ]}},
]});
const values = plan.at(localSeconds); // values['panel/x'], values['panel/detail/opacity']
```

Python: `compile_nested_sequence` من `motion_plan.py` بنفس JSON و`plan.at(t)`. كل مستوى له markers محلية؛ `at` رقم، marker محلي، `{label,offset}`، أو `<` لبداية العنصر السابق و`>` لنهايته. نهاية العنصر المتداخل = بدايته + آخر نهاية بداخله، بما فيها الفراغات الأولية. `>` يتبع ترتيب `items` في نفس المستوى. IDs فريدة بين الأشقاء، أحرف ASCII وأرقام و`_`/`-`؛ مسارات tracks لا تحتوي `/` لأن أسماء المجموعات تضيفه. أقصى عمق 8 وأقصى 512 عنصرًا؛ الدورات والتداخل الفعلي على track واحدة تُرفض. يُسمح بتسامح `1e-12` ثانية لتطبيع فرق الكسور العشرية عند حدود متلاصقة فقط.

الخطة تُسطَّح مرة قبل الرندر وتحتفظ بنسخة، وتعيد `from` قبل أول clip لكل track وتثبت `to` بعده. **هذا لا يخفي العنصر قبل بدايته**: استخدم بوابات VO وpresence الصريحة حتى لا تظهر حقيقة أو copy قبل نطقها. يمكن تحديد `timeScale` على عنصر sequence فقط: رقم 0.01–100 يضرب بدايات ومدد الطفل، بما فيها علاماته المحلية؛ 2 يضاعف المدة و0.5 ينصفها. تتضاعف المقاييس المتداخلة، ويستخدم `>` النهاية المعدَّلة. تُرفض المدد الأصغر من 1e-9 ثانية أو غير القابلة للتمثيل. لا تكرار للتسلسل الفرعي أو مراجع marker للأب أو تعديلات حية؛ يمكن تأليف هذه الحالات صراحة ضمن الحدود المتاحة. `duration` للحساب فقط وليست إذنًا بتمديد مدة الفيلم.

## مورف SVG مغلق بعد الاستيراد

```js
import {compileSvgMorph} from '../lib/svg-morph.js';
import {drawSvgArt} from '../lib/svg-canvas.js';
// a وb خرجان صالحان من tools/svg_compile.py
const morph = compileSvgMorph({version:1, from:a, to:b, count:32});
const plan = morph.at(progress); // progress رقم صريح؛ يُحصر بين 0 و1
// استخدم plan مع drawSvgArt في K أو SvgArt في R.
drawSvgArt(ctx, plan, {x:190,y:550,width:700,height:700});
```

في P: `from svg_morph import compile_svg_morph` و`morph.at(progress)` ثم `draw_svg_art`. اجمع الأصول وافحصها أولًا بعقد [SVG المحدود](motion-svg.md)، ثم أنشئ morph مرة واحدة قبل الإطارات؛ لا تعِد التحقق الهندسي في كل إطار.

- يطابق الأشكال وcontours **بترتيبها المؤلَّف**؛ يجب أن يتطابق viewBox، وعدد الأشكال، وعدد الحلقات، وID وألوان وحدود كل شكل. يجب أن تكون كل contours مغلقة. لا اختراع للحلقات أو مطابقة تلقائية للثقوب، ولا تغيير topology أو مزج ألوان أو stroke. لا تضمن المطابقة الدلالية: المؤلف يتحقق من ترتيب الحلقات المقصود.
- اختياريًا `matchById:true` في JS وPython يطابق IDs بدل ترتيب الأشكال؛ استعمل
  `--preserve-ids` عند تجميع الملفين. إذا اختلف ترتيب الرسم بين الطرفين، يبقى ترتيب المصدر
  ثابتًا، ولا يقبل الانتقال إلا عند انفصال صناديق الحركة المحافظة لكل الأشكال طوال المسار
  (صندوق الطرفين مع هامش نصف عرض stroke). هذا متحفظ وقد يرفض حركة سليمة؛ لا يطابق
  الحلقات تلقائيًا ولا يثبت صحة المعنى أو الحواف. المفتاح الافتراضي `false` يحافظ على السلوك السابق.
- يعيد أخذ 8–64 نقطة متساوية المسافة لكل حلقة (الافتراضي 24)، بحد إجمالي 192 نقطة و8 أشكال، ويحاذي اتجاه/بداية الحلقة. لذلك حتى النهايات **تقريب متعدد الأضلاع** وليست الأصول المنحنية بدقة تامة؛ قد تختفي تفاصيل صغيرة. زد العدد ضمن الحد وافحص الكادر.
- يفحص تغيّر أضلاع وحلقات كل shape على مدى progress كله بأسلوب محافظ: انكماش الأطراف/المساحة، تداخل الأضلاع أو الحلقات، وعلاقة الاحتواء في النهايات. يستخدم حدودًا عددية وتقسيمًا محدودًا حتى عمق 12 وميزانية 50000 اختبار لكل shape؛ إذا تعذّر إثبات الفصل يرفض الخطة، حتى لو كان الانتقال صالحًا نظريًا. الفحص يخص المضلعات المعيّنة نفسها، لا منحنيات SVG الأصلية أو التداخل بين shapes مستقلة. حسابات floating point ليست برهانًا رسميًا لكل مدخل عددي؛ راجع النتيجة بصريًا.
- لا دعم morph لمسارات مفتوحة أو أعداد حلقات مختلفة، ولا SVG DOM/CSS أو filters عامة. يمكن استخدام تدرج محلي محدود ثابت ومتطابق في الطرفين كما في [عقد SVG](motion-svg.md)، بلا تحريك تلقائي لألوانه. لم تتحول حالة SVG العامة أو morph العام إلى مكتملة.


## بديل للتكوينات غير المتوافقة: تلاشي، لا morph هندسي

إذا اختلف عدد الأشكال أو الحلقات يمكن الانتقال بين خطتي SVG صالحتين بتلاشي الطبقات، دون
اختراع topology أو الادعاء بانتقال هندسي. في K:

```js
import {drawSvgCrossfade} from '../lib/svg-canvas.js';
drawSvgCrossfade(ctx, fromPlan, toPlan, authoredProgress,
  {x:190,y:550,width:700,height:700});
```

في P استخدم `draw_svg_crossfade(image, from_plan, to_plan, amount, placement)`؛ في R استخدم
`<SvgCrossfade from={fromPlan} to={toPlan} amount={authoredProgress} x={190} y={550} width={700} height={700}/>`.
تُرسم المجموعة الأولى بـ`1-amount` ثم الثانية بـ`amount` فوق الخلفية؛ ذلك ليس مزجًا خطيًا محايدًا
في مناطق التداخل، وقد تظهر الخلفية أثناء التلاشي. كل أصل يرسم داخل مستطيل placement نفسه ويحتفظ
بـviewBox وتعبئته وثقوبه. لا تقبل placement إلا x/y/width/height؛ stroke كامل في كلا الأصلين. القيم صريحة من 0 إلى 1، ويُتحقق من الخطتين حتى عند النهايات.
في P وK حد الصورة/الكَنڤاس 4,194,304 بكسل؛ K يدعم transform ثنائي الأبعاد finite ويتطلب `source-over`، ويستخدم
canvas مؤقتًا لكل استدعاء، لذا قِس الأداء عند الاستخدام الكثيف. لا يتتبع semantic pairing ولا VO؛
على المؤلف إبقاء الحقائق تحت بواباتها. لا ضمان تطابق الحواف أو الألوان عبر المحركات.

## التحقق

```bash
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 -m pytest tests/test_motion_nested_morph.py -q
python3 tools/visual_verify.py --out cache/new-nested-morph-proof --morph --replay --remotion
bash tools/ci.sh
python3 tools/selftest.py --remotion --hybrid
```

المعاينة اختبار اصطناعي: P/K/R وثقب واحد، وK صامت وreplay عكسي؛ ليست ضمان تكافؤ pixels أو توقيت VO. يشمل الاختبار رفض تبديل ثقبين بين طرفين صالحين عندما تتقاطع مساراتهما في المنتصف.
