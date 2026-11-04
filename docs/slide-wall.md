# 3D Slide Wall (Phase 2B) — شرائح ثلاثية الأبعاد داخل Fixed Stage

`Slide Wall` مساحة شرائح مستقلة الهوية داخل **CONTENT** في Fixed Stage. لا ينشئ Stage أو VO Clock جديدين: نافذة `win(t)`، والقصّ، وترتيب `UNDER → CONTENT → OVER`، والكابشن، والهوية، و`text-direction.json` تظل تحت عقود Phase 2A الحالية.

المرجع الخارجي كان `majedphotos/video-ad-editor` Stage Wall عند `a69492d` (MIT، Majed Alzaabi 2026). أُعيد استخدام **مفاهيم** grid والكاميرا الموجّهة بالزمن والهبوط داخل الشريحة وmatch cut، لا محرك Three.js أو الكود غير المرتبط. Three.js اختياري وغير مستخدم هنا.

## الملفات والحدود

| الوحدة | المسؤولية |
|---|---|
| `procedural-reels/slide_wall.py` | التحقق/التطبيع، timeline والكاميرا، projection وhomography، ومحول P بخامات RGBA وOpenCV warp |
| `render/lib/slide-wall.js` | النواة المشتركة K/R؛ نسخة R مطابقة بايت ببايت |
| `space3d.py` / `space3d.js` | mesh وpinhole projection الأصليان، مع `look_camera` / `lookCamera` للـposition/target/up/roll |
| `render/lib/slide-wall-canvas.js` | محول K: slab meshes + خامات Canvas2D ومثلثات affine عندما لا يكون الوجه مستطيلًا |
| `remotion/src/lib/SlideWall.tsx` | محول R: SVG لجوانب slab وCSS `matrix3d` للوجه؛ محتوى الشريحة DOM حقيقي |
| `medo-motion/examples/slide-wall/` | مثال أرقام عام بلا branding أو ادعاءات factual، عبر scaffold حقيقي |
| `tools/new_slide_wall_example.py` | إنشاء مشروع P أو K أو R كامل خارج Git |
| `tools/reel_lint.py` (`W00/W01`) | فحص الخطة اختياريًا مع `beats.duration` |

لا توجد dependency إلزامية جديدة. P يستخدم OpenCV/Numpy الحاليين، K يستخدم Canvas2D الحالي، وR يستخدم React/Remotion الحاليين.

## عقد `plan/slide-wall.json`

الملف اختياري. وجوده يفعّل التحقق الصارم في `reel_lint` وفي K/R render launchers، ويتضمنه توقيع P chunk cache تلقائيًا مع بقية `plan/*.json`.

```json
{
  "version": 1,
  "id": "stable-wall-id",
  "clock": "vo",
  "backgroundRole": "ink_shadow",
  "canvas": { "w": 1080, "h": 1920, "fps": 30 },
  "viewport": { "x": 90, "y": 160, "w": 900, "h": 1200, "r": 48 },
  "camera": {
    "fov": 32,
    "overview": {
      "position": [0, 0, 24],
      "target": [0, 0, 0],
      "up": [0, 1, 0],
      "roll": 0
    }
  },
  "layout": {
    "slideSize": [3, 4],
    "gridColumns": 2,
    "gap": [0.45, 0.45],
    "origin": [0, 0, 0],
    "depth": 0.12,
    "preventOverlap": true,
    "bounds": { "min": [-10, -10, -2], "max": [10, 10, 2] }
  },
  "slides": [
    { "id": "slide-01" },
    {
      "id": "slide-02",
      "position": [2, 0, 0.2],
      "rotation": [0.05, -0.1, 0],
      "size": [3, 4],
      "surfaceRole": "paper",
      "edgeRole": "gray_2",
      "accentRole": "red"
    }
  ],
  "timeline": [
    { "mode": "overview", "start": 0, "end": 1 },
    {
      "mode": "move",
      "from": { "type": "overview" },
      "to": { "type": "slide", "slide": "slide-01" },
      "start": 1,
      "end": 2,
      "ease": "cubicInOut",
      "lift": 0.3
    },
    { "mode": "slide", "slide": "slide-01", "start": 2, "end": 3 }
  ]
}
```

### الهندسة والهوية

- `slides[].id` نص غير فارغ وفريد ومستقر. الحد الأقصى 64 شريحة في wall.
- `position = [x,y,z]` بوحدات world، و`rotation = [rx,ry,rz]` بالراديان، و`size = [width,height]` كاملين. `depth` سماكة كل slab وليس موضع z.
- عند حذف `position` يتولد grid متمركز حتميًا من ترتيب المصفوفة و`gridColumns` و`gap` و`origin`. التطبيع يحفظ الموضع الناتج؛ لا randomness ولا وقت نظام.
- `bounds`، إن وجد، يُختبر على **الزوايا الثماني المحوّلة** لكل slab. يجب أن يكون `min < max` في كل محور.
- عقد الفصل الافتراضي `preventOverlap=true` محافظ عمدًا: تؤخذ الزوايا الثماني المحوّلة لكل slab (بما فيها `rotation` و`depth`)، ثم يُختبر تداخل **XY AABB** لكل زوج. لذلك قد يرفض مضلعين منفصلين فعليًا إذا تداخل صندوقاهما المحافظان، لكنه لا يتجاهل اتساعًا ناتجًا عن الدوران. ملامسة الحواف مسموحة، ولا يُستخدم z للسماح بالتداخل. للتكديس المتعمد استخدم `preventOverlap=false`.
- `surfaceRole` و`edgeRole` و`accentRole` و`backgroundRole` أسماء أدوار brand فقط؛ الألوان الخام مرفوضة.
- `viewport` الافتراضي هو كامل canvas. عند Fixed Stage مرّر `stageState.win` في كل evaluation بدل الافتراضي الثابت.

### VO timeline والحركة

الأزمنة مطلقة على VO، وليست scene-local أو wall-clock. يبدأ أول segment عند `0`، وكل segment يلامس التالي تمامًا. يُرفض gap أو overlap أو مدة غير موجبة أو قيمة غير finite. عند تمرير `duration` للفحص يجب أن يساوي آخر `end` مدة المشهد/VO.

الأنماط الثلاثة فقط:

1. `overview`: hold لكل الحائط.
2. `slide`: hold على شريحة محددة، وهو موضع القراءة الأساسي.
3. `move`: انتقال بين endpointين مختلفين. يجب أن يساوي `from` نهاية ما قبله، و`to` بداية ما بعده.

الـeasing المسموح من مفردات `motion` الحالية: `linear`, `cubicInOut`, `cubicOut`, `quintOut`, `sineInOut`, `expoInOut`. النهايتان `u=0/1` ترجعان endpoint حرفيًا بلا easing drift. `lift >= 0` يضيف `sin(πu) * lift` إلى z للكاميرا، والـroll يسلك أقصر قوس.

أثناء `move` يُستخرج quaternion من basis الكاميرا المتعامدة `(right, up, -forward)` بلا roll. الحركات غير شبه المتطابقة تستخدم shortest-arc **SLERP** للاتجاه، بينما تحتفظ الحركات الصغيرة شبه المتطابقة بمسار normalized linear interpolation السابق حرفيًا لضمان التوافق. في مسار SLERP يتحرك موضع الكاميرا وtarget metadata خطيًا وبشكل مستقل، ثم يُطبق roll الأقصر والـlift كما كانا. لذلك لا ينهار `up` عند دوران 180°، وتبقى النهايتان والـeasing وreduced-motion cut كما هي.

`camera.overview` اختياري. بدونه تُحسب مسافة تتسع للزوايا كلها مع هامش 15%. لأن الحساب يستخدم viewport الحالي، استخدم `overview` الصريح إذا أردت تكوينًا ثابتًا بينما Fixed Stage نفسه يتحرك.

في focus تُستخدم basis الشريحة (`right/up/normal`) وFOV ومركز/أبعاد viewport. الوجه الأمامي يطابق viewport عندما يتساوى aspect ratio؛ وإلا يستخدم contain-fit على أحد البعدين. لا يتم التقريب نحو world origin بشكل أعمى.

في `motionMode="reduced"` يعرض `move` endpoint الهدف طوال segment كقطع مباشر، بلا interpolation أو lift؛ لا تتغير معلومة الشريحة المستهدفة. بقية سياسة reduced motion في Fixed Stage والمشاهد لا تتغير.

## التكامل الصحيح مع Fixed Stage

الـwall ليس wrapper لـFixed Stage؛ هو `drawContent` أو `children` فقط:

- **P:** أرجع `WALL["render"](t, viewport=state["win"], motion_mode=...)` من `content_fn` داخل `render_fixed_stage`.
- **K:** مرّر callback إلى `renderFixedStage(..., {drawContent})` واستدعِ `wall.draw` بـ`stageState.win`. المشهد اليدوي يعلن `manualFixedStage=true`؛ وإذا أعلن دعم reduced يعلن `supportsReducedMotion=true`.
- **R:** ضع `<SlideWall viewport={stageState.win}>` كدالة children داخل `<FixedStage>`. لا تضع captions داخل canvas الشريحة؛ أبقها في OVER.

لا تُستخدم خامة الشريحة الثابتة كساعة ثانية. أي نص داخلها يرسم في حالته المقروءة المستقرة، بينما الكاميرا وحدها تتحرك على VO. المحتوى المتحرك داخل الشريحة ليس جزءًا من هذا العقد الصغير.

## match cut

عند `slide` hold تكون كاميرا الوجه ثابتة ومحسوبة إلى viewport نفسها. يمكن بدء المشهد التالي بنفس دالة رسم الشريحة (P/K) أو نفس React content (R) في أول فريم، ثم القطع لبقية المشهد. للمطابقة حافة-بحافة اجعل aspect ratio الشريحة يساوي `win.w / win.h`. هذا **match-cut opportunity** وليس crossfade أو shared-element engine جديدًا.

## النص وlayout audit

- **R:** الوجه DOM، ولذلك `DirectedText` وHarfBuzz/RTL وDOM AABB capture يستمرون بعد CSS projection.
- **P/K:** النص داخل RGBA/Canvas texture لا يمكن لأداة screen-space الأصلية اكتشافه تلقائيًا. المحول يقبل `slide_layout` / `slideLayout` التي ترجع مستطيلات محافظة `{id,text,x,y,w,h,zone?}` بإحداثيات texture. تُسقط الزوايا عبر نفس homography، ويؤخذ AABB ويقص إلى `win(t)`، ثم يسجل في `layout_p` / `layout.js`.
- في overview/holds تسجل مستطيلات الشرائح النشطة. في `move` تسجل مستطيلات شرائح endpoints فقط؛ النص العرضي في الشرائح الأخرى أثناء الطيران ليس hold مقروءًا ويظل يحتاج مراجعة بصرية.
- هذه مستطيلات محافظة وليست pixel segmentation أو إثبات occlusion/readability. المراجعة البصرية والرندر الفعلي مطلوبان، خصوصًا للنصوص المتعددة أو الشرائح المتقاطعة بصريًا.

## حدود التنفيذ

- لا توجد مصادفة random أو mutable global camera/time. الخامات الثابتة cache محلية للمشهد فقط.
- الشرائح التي يدخل وجهها خلف near plane تُتخطى كاملة بدل إنشاء مضلع غير finite؛ لا يوجد near-plane splitting في Phase 2B.
- K لا يستطيع تحويل صورة إلى quad عام بعملية Canvas2D واحدة؛ لذلك يستخدم tessellation حتميًا (`subdivision=6` افتراضيًا، 1..16)، مع fast path للمستطيل المصفوف.
- **المطلوب هو numeric parity للكاميرا/projection/homography، لا pixel equality** بين OpenCV وCanvas2D وCSS/browser rasterization. لكل محرك render smoke مستقل.
- P وK لا يستنتجان مضمون texture تلقائيًا؛ أعد استخدام directed text ووفّر مستطيلات layout المحافظة. R يستخدم DOM مباشرة.
- المثال صامت ومدته 6 ثوانٍ للاختبار فقط. الإنتاج يجب أن يشتق `beats.json` ونهاية timeline من VO مقاس فعلًا، ولا يستخدم مدة المثال كنص بديل.

## الاختبارات

حد التسامح الموثق لاختبار parity الكاميرا بين Python وJavaScript، بما فيه حالة دوران 180°، هو `1e-8`؛ وتظل مقارنة projection/homography وAABB ضمن `1e-9` في fixtures الحتمية. لا يعني ذلك تطابق pixels بين المحركات.

```bash
# Fast unit/parity/adapter/layout checks (the real render smokes remain skipped).
python3 -m pytest -q tests/test_slide_wall.py -m 'not slow'

# Explicit real P/K/R renders. Prepare the documented Python/Node/Chromium runtimes first.
SLIDE_WALL_RENDER_SMOKE=1 \
MEDO_REMOTION_TEST_NODE_MODULES=/absolute/prepared/remotion/node_modules \
python3 -m pytest -q tests/test_slide_wall.py -m slow
```

لا تضاف رندرات Phase 2B الكاملة إلى PR CI؛ يغطي fast path العقد وnumeric parity وlayout، بينما يبقى الفيديو الكامل opt-in/nightly أو تحققًا محليًا موثقًا.
