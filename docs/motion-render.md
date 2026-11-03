# المرحلة الرابعة: خيارات الرندر والموارد والقياس

الأدوات هنا **اختيارية ومحدودة**، ولا تبني واجهة أو تعتمد على `prefers-reduced-motion` في جهاز الرندر. لتقليل الحركة اختَر صراحةً بدائل لعناصر زخرفية، دون تغيير طول الفيلم أو توقيت الحقائق أو الـVO.

## تقليل الحركة

```js
import {compileMotionPolicy} from '../lib/render-policy.js';
const policy = compileMotionPolicy({version:1,reduced:true,decorative:[
  {track:'orb.rotation',value:0},
]});
// بعد حساب values من الخطة عند t المحلي:
const safeValues = policy.at(values);
```

Python: `compile_motion_policy` من `render_policy.py`، بنفس صيغة البيانات. `reduced:false` يمرر القيم؛ `true` يثبت **فقط** tracks المحددة عند أرقام صريحة. يجب أن تكون tracks موجودة ورقمية؛ لا يُعدل باقي القيم أو الزمن. لا يمكن للأداة معرفة ما إذا كان track زخرفيًا: المؤلف مسؤول عن عدم اختيار إظهار حقيقة أو نص/opacity gated أو موضع يغيّر المعنى. هذا ليس switch عامًا يعيد تأليف جميع المشاهد تلقائيًا ولا يغني عن فحص إتاحة الحركة والـVO.

## الوضع الإنتاجي الاختياري — المرحلة السادسة

الافتراضي دائمًا `normal`؛ لا قراءة لتفضيل الجهاز ولا تغيير للـVO أو duration. استخدم متغير البيئة
`MEDO_MOTION_MODE=normal|reduced` مع P/K/R/Hybrid، أو `--motion-mode reduced` في K وR وHybrid
و`tools/render_p_segment.py`. مثال:

```bash
MEDO_MOTION_MODE=reduced python3 run_all.py                       # داخل مشروع P
node src/render.js --motion-mode reduced --out cache/reduced      # K
node scripts/render.mjs --motion-mode reduced --out out/r.mp4     # R
python3 tools/render_hybrid.py --project projects/demo --motion-mode reduced --out projects/demo/out/hybrid-reduced.mp4
```

- P: نموذج `scenes.py` يثبت زمن خلفية grid/dust فقط. المشهد المخصص يجب أن يعلن
  `SUPPORTS_REDUCED_MOTION = True` **ويؤلف بنفسه البديل**؛ إعلان العلامة وحده لا يزيل الحركة.
  سجلات `chunks.sig` وملفات `.mode` تمنع إعادة استخدام chunk من الوضع الآخر، حتى عند تشغيل `chunk.py` مباشرة.
- K: في المشاهد النشطة في نطاق الرندر يجب إعلان `export const supportsReducedMotion = true`،
  واستخدام `motionMode` في `init`/`draw` لتنفيذ البديل المقصود. النموذج الأول يثبت المربع الزخرفي فقط؛
  بقية أمثلة K غير معلنة، لذلك رندر النطاق الكامل المخفّف يفشل حتى يؤلفها صاحب المشروع ويصرّح بها.
  المشاهد خارج النطاق لا تُهيّأ في الوضع المخفّف؛ طلب إطار خارجه يُرفض. الوضع العادي يحتفظ بتهيئة جميع المشاهد.
- R: خاصية `motionMode` في `MotionReel` تثبت نبض كرة الخلفية فقط. على صاحب المكوّن المخصص تمرير
  الخاصية وتأليف البدائل؛ لا يفحص Remotion تلقائيًا امتثال مكونات أخرى. Hybrid يمرر الوضع لكل المحركات.

توقيت الحقائق والنص الموجَّه وساعة المشهد تبقى كما هي في الأمثلة. قد تبقى حركات أخرى؛ المؤلف مسؤول عن عدم
تثبيت حقيقة أو بوابة ظهور، وعن المراجعة البصرية والإتاحة. هذا ليس شهادة إتاحة أو وضعًا عامًا يعيد تأليف الفيديو.

## حساب دفعة واحدة وموارد صريحة

`compileFrameBatch([{id,sample},...])` / `compile_frame_batch`: ينفذ sampler النقي نفسه مرة في كل
استدعاء `at(t)`، بدون تخزين بين إطارات أو seeks. اعتبر الناتج المشترك immutable؛ لا batching شامل لـDOM/GPU.

K يعطي كل مشهد scope منفصلًا في `init({resources,...})` و`draw(...,{resources,...})`؛ سجّل به
`resources.defer(() => dispose())`. تُنتظر كل تهيئات المشاهد ثم تُغلق scopes بالعكس بعد النجاح أو الفشل،
والتنظيف داخل كل scope بترتيب LIFO ويستمر عند الخطأ. في P يمكن تعريف
`def init_resources(scope): ...` في `scenes.py` وتسجيل `scope.defer(dispose)`؛ ينظف كل chunk أو segment
بعد الرندر أو الخطأ، ولا يُستدعى hook عند cache hit. على المؤلف تسجيل الموارد نفسها وعدم الاعتماد على حالة
إطار سابق. الإغلاق متكرر وآمن؛ لا تنتظر `scope.close()` من داخل disposer تابع لنفس scope لأنه سيعلق.
R يوفّر `createResourceScope()` يدويًا فقط، ولا نضمن دورة حياة عامة لمكوّنات Remotion أو cleanup عند إنهاء
قسري للعملية. لا ضمان للتنظيف بعد قتل العملية أو crash في أي محرك.

## قياس محلي اختياري

- K: `node src/render.js --profile --out cache/fresh --name proof` يكتب `render-profile.json` بدون overwrite.
  frame evaluation يتضمن IPC، وcapture/write يتضمن data URL وفكها وكتابة القرص أو انتظار backpressure؛
  encoderFinalizeMs يقيس flush المتبقي **فقط** لأن FFmpeg يعمل بالتوازي. في audit لا يوجد capture/write
  أو encoder وwall يتضمن replay إن طُلب. wall ينتهي قبل تنظيف scopes.
- P segment: `python3 tools/render_p_segment.py ... --profile-out cache/fresh-profile.json` يكتب زمن
  تهيئة أولي قبل hook، وتوزيع render/write وflush المتبقي. `run_all.py` لا يكتب profile تلقائيًا.
- R: `node scripts/render.mjs ... --profile` يكتب `<output>.profile.json` دون overwrite؛ renderMs
  وقت subprocess يشمل bundle والمتصفح والالتقاط والترميز. Hybrid: `python3 tools/render_hybrid.py ... --profile`
  يكتب بجانب الفيلم توقيت subprocess لكل segment والتحقق ثم assembly وwall الكلي.

هذه الأرقام خاصة بالآلة والتشغيل وليست benchmark أو GPU attribution؛ لا نجمع أزمنة متداخلة كأنها مراحل
مستقلة. الفحص لا يغيّر قيمة الوقت التي يراها المشهد أو الصوت. اختبر الوضعين:

```bash
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 -m pytest tests/test_motion_production.py -q
bash tools/ci.sh
python3 tools/selftest.py --remotion --hybrid
python3 tools/selftest.py --remotion --hybrid --reduced-motion
```

مكوّنات `GeometryBindings` و`SvgArt` في R ذات أنواع ومحددات وليست ربطًا عامًا لكل CSS/3D.
[عقد SVG المحدود](motion-svg.md)؛ [حالة كل ميزة](motion-rollout.md).
