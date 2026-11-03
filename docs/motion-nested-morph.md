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

الخطة تُسطَّح مرة قبل الرندر وتحتفظ بنسخة، وتعيد `from` قبل أول clip لكل track وتثبت `to` بعده. **هذا لا يخفي العنصر قبل بدايته**: استخدم بوابات VO وpresence الصريحة حتى لا تظهر حقيقة أو copy قبل نطقها. لا time-scale أو تكرار للتسلسل الفرعي أو مراجع marker للأب أو تعديلات حية؛ يمكن تأليف هذه الحالات صراحة ضمن الحدود المتاحة. `duration` للحساب فقط وليست إذنًا بتمديد مدة الفيلم.

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
- يعيد أخذ 8–64 نقطة متساوية المسافة لكل حلقة (الافتراضي 24)، بحد إجمالي 192 نقطة و8 أشكال، ويحاذي اتجاه/بداية الحلقة. لذلك حتى النهايات **تقريب متعدد الأضلاع** وليست الأصول المنحنية بدقة تامة؛ قد تختفي تفاصيل صغيرة. زد العدد ضمن الحد وافحص الكادر.
- يفحص تغيّر أضلاع وحلقات كل shape على مدى progress كله بأسلوب محافظ: انكماش الأطراف/المساحة، تداخل الأضلاع أو الحلقات، وعلاقة الاحتواء في النهايات. يستخدم حدودًا عددية وتقسيمًا محدودًا حتى عمق 12 وميزانية 50000 اختبار لكل shape؛ إذا تعذّر إثبات الفصل يرفض الخطة، حتى لو كان الانتقال صالحًا نظريًا. الفحص يخص المضلعات المعيّنة نفسها، لا منحنيات SVG الأصلية أو التداخل بين shapes مستقلة. حسابات floating point ليست برهانًا رسميًا لكل مدخل عددي؛ راجع النتيجة بصريًا.
- لا دعم morph لمسارات مفتوحة أو أعداد حلقات مختلفة، ولا SVG DOM/CSS أو gradients/filters. لم تتحول حالة SVG العامة أو morph العام إلى مكتملة.

## التحقق

```bash
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 -m pytest tests/test_motion_nested_morph.py -q
python3 tools/visual_verify.py --out cache/new-nested-morph-proof --morph --replay --remotion
bash tools/ci.sh
python3 tools/selftest.py --remotion --hybrid
```

المعاينة اختبار اصطناعي: P/K/R وثقب واحد، وK صامت وreplay عكسي؛ ليست ضمان تكافؤ pixels أو توقيت VO. يشمل الاختبار رفض تبديل ثقبين بين طرفين صالحين عندما تتقاطع مساراتهما في المنتصف.
