# One-Take (Phase 2C) — مشهد واحد بكاميرا وتفاعل مستمرين

`One-Take` عقد صغير لمشهد UI/product explainer واحد: عناصر مستقرة، semantic states مرتبة، كاميرا 2D مستمرة، ومسار cursor حتمي. لا ينشئ محرك حركة عامًا ولا VO Clock أو Fixed Stage جديدين.

المرجع التقني كان `majedphotos/video-ad-editor` One-Take عند `a69492d` (MIT، Majed Alzaabi 2026). أُعيد استخدام أفكار **absolute time، camera/state continuity، cursor interpolation، وclick feedback** فقط؛ لم يُنسخ محرك أو مشهد أو أصل من المرجع.

## الملفات والحدود

| الوحدة | المسؤولية |
|---|---|
| `procedural-reels/one_take.py` | التحقق والتطبيع والتقييم النقي، strict project loader، ومحول P بخامات RGBA وOpenCV |
| `render/lib/one-take.js` | النواة المشتركة K/R؛ نسخة R مطابقة بايت ببايت |
| `render/lib/one-take-canvas.js` | محول K بخامات Canvas2D، directed text، cursor/ring، layout registration، وresource cleanup |
| `remotion/src/lib/OneTake.tsx` | محول R: عناصر DOM حقيقية و`DirectedText` وSVG cursor/click |
| `medo-motion/examples/one-take/` | مثال Today أصلي صامت من ثماني حالات، عبر P/K/R |
| `tools/new_one_take_example.py` | إنشاء مشروع P أو K أو R كامل خارج Git |
| `tools/reel_lint.py` (`O00/O01`) | فحص `plan/one-take.json` اختياريًا مع `beats.duration` |

لا توجد dependency إلزامية جديدة. وجود الملف يفعّل التحقق في lint وK/R launchers، لكنه **لا يستبدل scene dispatcher تلقائيًا**: مشهد P أو K أو composition في R يستدعي المحول صراحة. كذلك تدخل كل ملفات `plan/*.json` في توقيع P chunk cache الحالي.

في P يقرأ `load_project_one_take` ملف `plan/beats.json` عند وجود One-Take، ويشترط `duration` موجبًا finite ومطابقًا تمامًا لمدة One-Take قبل إنشاء المحول أو أي frame. غياب One-Take يحافظ على `None` دون قراءة beats؛ أما غياب duration الصالح مع وجود One-Take فهو خطأ. القاعدة نفسها تمر في lint وK/R launchers.

## عقد `plan/one-take.json`

```json
{
  "version": 1,
  "id": "product-take",
  "clock": "vo",
  "duration": 8,
  "canvas": { "w": 1080, "h": 1920, "fps": 30 },
  "backgroundRole": "gray_1",
  "elements": [
    { "id": "card", "kind": "rect", "w": 620, "h": 170, "radius": 32, "role": "paper" },
    { "id": "title", "kind": "text", "w": 500, "h": 100, "text": "Today", "fontRole": "title", "fontSize": 72, "role": "ink", "rtl": false }
  ],
  "states": [
    {
      "id": "opening", "time": 0,
      "camera": { "x": 540, "y": 960, "zoom": 0.88 },
      "elements": {
        "card": { "x": 540, "y": 900 },
        "title": { "x": 540, "y": 600 }
      }
    },
    {
      "id": "result", "time": 8, "ease": "cubicInOut",
      "camera": { "x": 540, "y": 960, "zoom": 1.05 },
      "elements": {
        "card": { "y": 1000, "scale": 1.1, "rotation": 0, "opacity": 1 },
        "title": { "y": 650 }
      }
    }
  ],
  "cursor": {
    "size": 42,
    "points": [
      { "time": 0, "x": 900, "y": 1550 },
      { "time": 8, "x": 540, "y": 1000, "ease": "cubicInOut" }
    ],
    "clicks": [{ "time": 2.2, "duration": 0.36 }]
  }
}
```

### العناصر والحالات

- `kind` أحد `rect` أو `circle` أو `text`. لكل عنصر `id` نصي فريد ومستقر، وأبعاد موجبة، وbrand `role` محجوز. `strokeRole` و`accentRole` اختياريان؛ الألوان الخام مرفوضة.
- النص يحتاج `fontRole` من أدوار Text Direction التسعة الحالية (`hook`, `title`, `body`, `keyword`, `cta`, `label`, `number`, `ui`, `quote`) و`fontSize` موجبًا و`rtl` boolean. تُرفض الأدوار غير المدعومة مثل `caption` و`hud` أثناء validation. لا HTML أو raw SVG أو external asset داخل هذا العقد.
- عدد الحالات من **2 إلى 16**، بأزمنة absolute VO متزايدة بصرامة. أول زمن `0` وآخر زمن يساوي `duration`؛ وعند تمرير مدة beats يجب أن تتطابق معها. كل الحالات لها IDs فريدة وكاميرا `{x,y,zoom>0}` كاملة.
- الحالة الأولى تحدد كل عنصر ظاهر بـ`x/y`، مع defaults موثقة: `scale=1`, `rotation=0`, `opacity=1`. الحالات التالية patches: القيم المحذوفة تُحمل من الحالة السابقة. كل مرجع عنصر يجب أن يكون معروفًا.
- `ease` على الحالة هو easing **الوصول إليها** من الحالة السابقة. القيم المسموحة: `linear`, `cubicInOut`, `cubicOut`, `quintOut`, `sineInOut`, `expoInOut`.
- `viewport` الاختياري `{x,y,w,h,r?}` يجب أن يبقى داخل physical canvas. بدونه يملأ المشهد canvas. لا يغير world coordinates؛ يغير screen mapping والقص فقط.

### التقييم والتفاعل

كل نتيجة دالة في `t` فقط والخطة المطبّعة. لا يوجد accumulated state أو random أو system time. القيم خارج المشهد تُقص إلى أول/آخر حالة، وعند الحدود ترجع endpoints حرفيًا. داخل segment:

- camera x/y وكل transforms تتداخل بالـeasing؛ zoom يتداخل بمنحنى لوغاريتمي، فتكون النسبة الهندسية مستمرة بلا قفزات.
- `x/y` مركز العنصر في world؛ screen position ينتج من الكاميرا وviewport، ثم يطبق scale/rotation/opacity. الـAABB الناتج محافظ للدوران.
- cursor points مرتبة داخل المدة وease كل نقطة يصف الوصول إليها. click عند `time` يرسى على **نقطة cursor المُقيّمة في اللحظة نفسها**، لا على موضع عشوائي أو hit-testing مستقل.
- `duration` للنقر موجب والنقرات غير متداخلة. visible press يستمر `min(0.14, duration/2)`، والring يتسع ويختفي خلال مدة النقرة. cursor وclicks اختياريان معًا؛ لا typing أو drag في Phase 2C.
- `motionMode="reduced"` يعرض target state طوال كل segment، ويثبت cursor عند نقطة المقطع التالية، ويلغي travel/press/ring. لا يحذف المعلومة المستهدفة.

## الاستخدام في P / K / R

**P** داخل `scenes.py`:

```python
from one_take import create_one_take, load_project_one_take

SPEC = load_project_one_take(ROOT)
TAKE = create_one_take(SPEC, direction=DIRECTION)
frame = TAKE["render"](absolute_t, motion_mode="normal")
```

`create_one_take` يبني static shape/text sprites مرة واحدة، ويسجل text boxes المحافظة في `layout_p`. لا يوجد mutable playhead في adapter.

**K** داخل scene `init/draw`:

```js
const spec = await loadOneTake();
const take = createOneTake(spec, {direction});
resources?.defer(() => take.close());
take.draw(ctx, absoluteT, {motionMode, viewport});
```

`loadOneTake` يرجع `null` إذا لم توجد الخطة، ويفشل برسائل واضحة للـHTTP/JSON/plan errors. المحول يستخدم `drawDirectedText` ويسجل مستطيلاته بعد camera transform.

**R** داخل composition:

```tsx
import spec from '../plan/one-take.json';
import {OneTake} from './lib/OneTake';

<OneTake spec={spec} direction={direction} time={frame / fps} motionMode={motionMode} viewport={viewport} />
```

R يستخدم DOM/CSS transforms و`DirectedText` الحقيقيين، لذلك يظل font loading وDOM AABB capture ضمن المسار الحالي. P/K يسجلان conservative boxes؛ هذا ليس pixel segmentation أو إثبات occlusion.

مع Fixed Stage مرّر `stageState.win` إلى `viewport` في كل frame، وضع One-Take داخل CONTENT فقط. لا تُنشئ Stage أو captions ثانية داخله. المثال الحالي fullscreen ولا يشغّل Fixed Stage.

## حدود التنفيذ

- النص داخل العنصر ثابت ومقروء؛ One-Take يملك outer transform فقط. لا per-word/per-character timeline أو text morph في هذا العقد.
- لا scene cuts أو scene fades أو motion blur أو media masks أو general-purpose motion presets. opacity خاص بالعنصر وليس crossfade بين مشاهد.
- المطلوب **numeric state/camera/transform parity** بين Python وJavaScript، لا pixel equality بين OpenCV وCanvas2D وDOM/browser rasterization. الاتجاه والتوقيت والعناصر واحدة؛ الخطوط وراسترة النص قد تختلف قليلًا.
- استخدم glyphs الموجودة فعلًا في الخط المختار. المثال يستخدم أرقام الإكمال `1/2/3` بدل checkmark غير المدعوم في Cairo على P.
- P/K text registration محافظ أثناء transforms، لكنه لا يقيس احتجاب عنصر خلف آخر. راجع representative frames والفيديو الفعلي.
- الخامات cache محلية للمشهد وليست state للزمن. K يحرر cached canvases عبر `close()`؛ P لا يحتفظ بframes، وR لا يضيف animation clock.
- المثال صامت 8 ثوانٍ للاختبار فقط. الإنتاج يشتق beats والنهاية من VO مقاس فعلًا ولا يستخدم مدة المثال كنص بديل.

## الاختبارات

fast tests تشمل validation، start/end، الحدود، interpolation/log zoom، transforms، interaction timing، reduced motion، determinism/shuffled seek، P rendering، strict loading/lint، وnumeric P/JS parity بحد `1e-9`. لا تعني هذه النتيجة تطابق pixels بين المحركات.

```bash
# Fast checks; real render smokes remain skipped.
python3 -m pytest -q tests/test_one_take.py -m 'not slow'

# Opt-in short real renders: P=3 H.264 frames, K=3 JPG frames,
# R=strict TypeScript + two identical stills. No full eight-second render.
ONE_TAKE_RENDER_SMOKE=1 \
MEDO_REMOTION_TEST_NODE_MODULES=/absolute/prepared/remotion/node_modules \
python3 -m pytest -q tests/test_one_take.py -m slow
```

جهّز Python/FFmpeg وChromium وRemotion dependencies بالمسارات الموثقة قبل الأمر الثاني. لا تُضاف الرندرات الكاملة إلى PR CI؛ fast path يعمل في CI، والرندرات القصيرة opt-in محليًا.
