# Fixed Stage (Phase 2A) — المسرح الثابت عبر المحركات الثلاثة (P / K / R)

يوفر نظام **Fixed Stage** إطار عرض مستمرًا وموحّدًا عبر المحركات الثلاثة (`P` Python/Pillow/OpenCV، و`K` Canvas2D/Chromium، و`R` React/Remotion) مع نافذة محتوى ديناميكية قابلة للتحريك والقصّ الحقيقي `win(t)` تحت سلطة **VO Clock** الكاملة.

> **Phase 2B:** يمكن وضع `3D Slide Wall` داخل CONTENT فوق النوافذ نفسها، بلا Stage أو ساعة منافسة. راجع [`docs/slide-wall.md`](slide-wall.md) للعقد والمحولات والمثال الكامل.

---

## ١) البنية المعمارية (Architecture)

يتجنب التصميم أي ازدواجية بين المحركات عبر تقسيم المسؤوليات إلى نواة رياضية موحّدة ومحولات خفيفة لكل محرك:

| الملف | الدور |
|---|---|
| `medo-motion/templates/procedural-reels/stage.py` | عقد التحقق والتطبيع `validate_stage_spec` / `normalize_stage_spec`، الدالة النقية `win(spec, t)`، قناع القصّ فائق المعاينة (`SS=4`)، ومركّب الطبقات الثلاث `render_fixed_stage` لمحرك `P` |
| `medo-motion/templates/render/lib/stage.js` | النواة المشتركة في JavaScript (مطابقة بايت ببايت مع نسخة Remotion، بدون أي اعتماديات خارجية) |
| `medo-motion/templates/remotion/src/lib/stage.js` | نسخة مطابقة بايت ببايت من `stage.js` لمحرك `R` مع توافق كامل مع `tsc --strict` |
| `medo-motion/templates/render/lib/stage-canvas.js` | محول محرك `K` فوق Canvas2D (`ctx.rect` / `ctx.roundRect` + `ctx.clip()`) مع تكامل `backgrounds.js` و`captions.js` و`layout.js` |
| `medo-motion/templates/remotion/src/lib/FixedStage.tsx` | مكوّن React/Remotion لمحرك `R` يطبق ترتيب الطبقات الثلاث وقصّ CSS الحقيقي `clip-path: inset(... round r)` |
| `tools/reel_lint.py` (`F00`–`F04`) | فحص اختياري لملف `plan/stage.json` مقابل `beats.json` و`copy.json` و`text-direction.json` و`word-timings.json` |

---

## ٢) عقد المواصفة (`StageSpec` / `plan/stage.json`)

جميع الألوان تُكتب حصريًا بأسماء أدوار الهوية المقفولة في `medo-motion/brand/brand.json` (الإصدار `v2.6`: الاثنا عشر لونًا الأساسية بالإضافة إلى الظل المشتق `ink_shadow` `#030303`). يُرفض أي كود لوني خام (`#RRGGBB` أو `rgb(...)`) كما يُرفض أي حقل شعار أو اسم قناة أو اسم سلسلة افتراضي (`logo`, `channelName`, `seriesName`, `watermark`).

```json
{
  "version": 1,
  "enabled": true,
  "id": "episode-stage",
  "clock": "vo",
  "theme": "dark",
  "canvas": { "w": 1080, "h": 1920, "fps": 30 },
  "defaultFramedBox": { "x": 56, "y": 224, "w": 968, "h": 1096, "r": 36 },
  "under": {
    "surfaceRole": "ink_shadow",
    "background": { "id": "wash", "theme": "dark", "density": 40, "angle": 0, "speed": 1.0 },
    "frame": {
      "enabled": true,
      "strokeRole": "red",
      "strokeWidth": 3,
      "matRole": "ink_shadow",
      "matAlpha": 0.36
    }
  },
  "timeline": [
    { "mode": "fullscreen", "start": 0.0, "end": 1.8 },
    {
      "mode": "transition",
      "from": "fullscreen",
      "to": "framed",
      "start": 1.8,
      "end": 2.4,
      "ease": "cubicInOut",
      "anchor": { "scene": 2, "word": 0, "text": "السبب" }
    },
    { "mode": "framed", "start": 2.4, "end": 7.2 },
    {
      "mode": "transition",
      "from": "framed",
      "to": "fullscreen",
      "start": 7.2,
      "end": 7.8,
      "ease": "cubicInOut"
    },
    { "mode": "fullscreen", "start": 7.8, "end": 9.6 }
  ],
  "over": {
    "progressBar": {
      "enabled": true,
      "y": 64,
      "height": 6,
      "marginX": 60,
      "trackRole": "paper",
      "trackAlpha": 0.18,
      "fillRole": "red"
    },
    "header": {
      "enabled": true,
      "slots": [
        {
          "id": "hdr-s2",
          "scene": 2,
          "copyId": "hdr-topic-s2",
          "role": "label",
          "start": 2.2,
          "end": 7.2,
          "x": 540,
          "y": 136,
          "size": 38,
          "maxWidth": 920,
          "colorRole": "paper",
          "accentRole": "salmon",
          "pillRole": "ink",
          "pillBorderRole": "red",
          "pillAlpha": 0.92
        }
      ]
    },
    "captions": { "enabled": true, "y": 1455 }
  }
}
```

### قواعد النص والـHeader الاختياري
- الـHeader معطّل افتراضيًا (`slots: []`)، ولا يوجد أي نص ثابت أو اسم سلسلة افتراضي.
- عند تفعيله لموضوع الحلقة أو سؤال المشهد أو عنوان الفصل المستخرج من السكريبت، **يُمنع كتابة `text` مباشر داخل `stage.json`**؛ يجب أن يشير كل slot إلى `copyId` معرّف في `plan/copy.json` وموجّه صراحةً بأسلوب حركة وخط في `plan/text-direction.json`.

---

## ٣) نافذة المحتوى الديناميكية `win(t)`

تُعرَّف نافذة المحتوى كدالة نقية عديمة الحالة:

```text
win(spec, t) -> { x, y, w, h, r }
```

- **وضع ملء الشاشة (`fullscreen`):** يعيد القيم الدقيقة `{ x: 0, y: 0, w: W, h: H, r: 0 }` دون أي تقريب عائم، وتتحقق منه الدالة `is_fullscreen_window(box)` / `isFullscreenWindow(box)`.
- **الوضع المؤطَّر (`framed`):** يعيد المستطيل الداخلي `{ x, y, w, h, r }` (الافتراضي `{ x: 56, y: 224, w: 968, h: 1096, r: 36 }` واقع بالكامل داخل منطقة المحتوى الآمنة `y: 200..1350` واتساع الهامش `>= 40px`).
- **الانتقالات الثنائية (`transition`):**
  - تدعم `fullscreen -> framed` و`framed -> fullscreen` و`framed A -> framed B`.
  - تستخدم استيفاءً محدبًا `a * (1 - p) + b * p` مع منحنيات حتمية (`cubicInOut`, `cubicOut`, `quintOut`, `quadInOut`, `linear`) وتحفظ نقاط البداية والنهاية بدقة تامة عند `p = 0` و`p = 1`.
  - يُرفض أي تداخل زمني بين المقاطع أو أي قفزة غير متصلة (`discontinuous jump`) بين نهاية مقطع وبداية المقطع الذي يليه.
- **تقييد نصف القطر ورفض الهندسة الفاسدة:**
  - يُقيد نصف القطر دائمًا ضمن `0 <= r <= min(w, h) / 2`.
  - تُرفض القيم غير الصالحة (`w <= 0`, `h <= 0`, `NaN`, `±Infinity`, القيم المنطقية `bool`, الأعداد الصحيحة الضخمة مثل `10**1000`, أو النوافذ الخارجة عن حدود اللوحة `[0..W] × [0..H]`).

---

## ٤) ترتيب الطبقات الثلاث والقصّ الحقيقي (Layers & True Clipping)

تلتزم المحركات الثلاثة بترتيب الرسم الصارم نفسه في كل إطار:

1. **`UNDER` (خلفية المسرح المستمرة):**
   - تُرسم خلف النافذة عندما لا يكون المسرح في وضع ملء الشاشة، وتستفيد من خلفيات الكتالوج (`backgrounds.py` / `backgrounds.js`) مع احترام `MEDO_MOTION_MODE=reduced` عبر `decorative_time`.
2. **`CONTENT` (محتوى المشهد والانتقالات مقصوصًا بـ`win(t)`):**
   - يحتوي على المشاهد الحالية وانتقالات المشاهد (`wipe`, `iris`, `slide`, `dissolve`...) مقصوصة بقناع حقيقي على حدود `win(t)`:
     - **المحرك `P`:** قناع ألفا فائق المعاينة (`SS = 4`) مع تصفير رياضي صارم خارج المستطيل وخارج قوس الزاوية الدائرية (`hypot(dx, dy) > r + 0.75`) وتخزين مؤقت نقي غير قابل للتعديل `@lru_cache` حسب الإحداثيات المكمّاة لربع بكسل.
     - **المحرك `K`:** مسار قصّ Canvas2D أصيل (`ctx.beginPath()` ثم `ctx.rect` عند `r == 0` أو `ctx.roundRect` عند `r > 0` متبوعًا بـ`ctx.clip()` داخل زوج `ctx.save()` / `ctx.restore()`).
     - **المحرك `R`:** خاصية القصّ الرسومي في Chromium (`clip-path: inset(top right bottom left round r)`) على حاوية `CONTENT` مع بقاء الإحداثيات الداخلية مطابقة لـ`1080×1920`.
   - **مسار التمرير المباشر (`Passthrough`):** عندما تكون `isFullscreen == true` تتخطى المحركات الثلاثة رسم `UNDER` وقناع القصّ بالكامل دون أي كلفة إضافية.
3. **`OVER` (العناصر الأمامية غير المقصوصة):**
   - تُرسم بعد إغلاق قناع `CONTENT`، وتشمل الـHeader الاختياري (`zone="hud"`)، والكابشن العربي (`zone="caption"`)، وشريط التقدم، وأي شارات أمامية مسموحة، فلا تتعرض أبدًا للقصّ بحدود `win(t)`.

### التفاوتات المقاسة عبر المحركات (Cross-Engine Tolerances)
- تتطابق معادلات `win(t)` و`stageStateAt(t)` بين Python (`stage.py`) وJavaScript (`stage.js`) بتفاوت عددي أقل من `1e-9` بكسل.
- عند حواف الزوايا الدائرية (`r > 0`) قد يختلف تنعيم الحواف (antialiasing) على الشريط الحدودي بعرض `1–2px` بين مرشح Pillow `BOX` (`SS=4`) ومحرك Skia في Canvas2D/CSS، بينما يتطابق الداخل الكامل والخارج الكامل بنسبة `0` تسريب لوني خارج `win(t)`.

---

## ٥) التوقيت الحتمي وVO Clock

- طول الريل وحدود المشاهد تأتي حصريًا من التعليق الصوتي المقاس (`tools/vo_length.py`).
- كل خاصية في المسرح دالة نقية في الزمن `f(t)`: لا توجد حلقات لا نهائية، ولا عدادات إطارات متراكمة، ولا اعتماد على الإطار السابق.
- نتيجة الإطار عند اللحظة `t` متطابقة تمامًا سواء جرى التقييم بالترتيب الأمامي، أو العكسي (`--replay`)، أو القفز العشوائي، أو الرندر المتوازي بالمقاطع (`chunk.py`) عند `30 FPS`.

---

## ٦) التكامل مع فحص التخطيط والمناطق الآمنة (3-Boundary Layout Audit)

تم توسيع أدوات الفحص الحالية (`layout_p.py` و`tools/layout_audit_p.py` في `P`، و`render/lib/layout.js` في `K`، و`remotion/src/lib/layout.tsx` في `R`) لفحص الحدود الثلاثة معًا دون إنشاء أداة موازية:

| الكود | الفحص |
|---|---|
| `L01` | خروج النص عن المنطقة الآمنة لدوره (`hud` / `content` / `caption`) أو هروب عنصر أمامي في `OVER` خارج الهامش الآمن |
| `L02` | تصادم نص مع نص آخر أو مع صندوق محمي `keep` (بما في ذلك التصادم العابر للطبقات بين `OVER` و`CONTENT` المرئي داخل `win(t)`) |
| `L03` | تصادم نص (عنوان أو Header أو كابشن) مع وجه المقدم المحمي `face` |
| `L04` | تداخل نص غير `hud` أو عنصر أمامي مع شريط واجهة المنصات الأيمن `PLATFORM_RIGHT_RAIL` (`x: 940..1080, y: 1100..1500`) |
| `L05` | امتداد نص داخل طبقة `CONTENT` خارج حدود المستطيل الديناميكي `win(t)` |
| `L06` | انقطاع نص أو حروف عربية داخل طبقة `CONTENT` بسبب قوس الزاوية الدائرية (`r > 0`) لنافذة `win(t)` |

كما توفر الدالة `stage_safe_envelope(win_box)` / `stageSafeEnvelope(winBox)` المستطيل الداخلي الآمن بعد خصم هامش الزوايا الدائرية `r * (1 - 1/sqrt(2)) + 8px` لضمان عدم ملامسة التشكيل أو الحروف العربية الطرفية (`أ`، `ل`، `ي`، `؟`) لأقواس الزوايا.

---

## ٧) التفعيل التلقائي عبر `plan/stage.json` والاستخدام البرمجي اليدوي

يدعم النظام نمطين متكاملين فوق النواة نفسها دون أي ازدواجية:

### أ) التفعيل التلقائي من إعدادات المشروع (`plan/stage.json`)
- ينشئ `tools/new_project.py` ملف `plan/stage.json` تلقائيًا في كل مشروع جديد مع `"enabled": false` افتراضيًا (بحيث يحافظ المشروع الجديد على السلوك السابق حرفيًا بملء الشاشة دون أي تغيير).
- المشاريع القديمة التي لا تحتوي أصلًا على `plan/stage.json` تعمل تلقائيًا بآلية التراجع الآمن (`fallback` إلى الوضع غير المفعّل) عبر المحركات الثلاثة — بما في ذلك التحميل الاختياري في `RemotionRoot.tsx` — دون الحاجة لأي خطوة ترحيل (`migration`).
- بمجرد ضبط `"enabled": true` داخل `plan/stage.json` وتجهيز `plan/beats.json` و`plan/copy.json` و`plan/text-direction.json`، تقرأ مسارات التشغيل الافتراضية في المحركات الثلاثة الإعداد وتطبّق المسرح الثابت تلقائيًا دون الحاجة لإعادة كتابة ملفات التشغيل:
  - **المحرك `P` (`scenes.py` / `render_frame`):** يستدعي `stage.load_project_stage()` ويغلف رسم المشهد والانتقالات داخل `render_fixed_stage`، كما تدخل ملفات `plan/*.json` ضمن بصمة التجزئة في `chunk_utils.build_signature`.
  - **المحرك `K` (`src/main.js`):** يجلب `/plan/stage.json` وملفات الخطة المرافقة ويغلف `scene.draw(...)` تلقائيًا عبر `renderFixedStage`.
  - **المحرك `R` (`src/RemotionRoot.tsx` + `scripts/render.mjs`):** يتحقق من `plan/stage.json` ويغلف محتوى `MotionReel` داخل `<FixedStage>` تلقائيًا.

### ب) الاستخدام البرمجي المباشر داخل مشاهد مخصّصة (`autoWrap: false`)
عند بناء مشهد مخصّص يستدعي الـAPI يدويًا مع وجود `plan/stage.json` مفعّل، يُضبط `"autoWrap": false` في `plan/stage.json` (أو يُصدَّر `export const manualFixedStage = true;` في مشهد محرك `K`) فيمتنع مسار التشغيل الافتراضي في `P` و`K` و`R` عن التغليف التلقائي منعًا لأي تغليف مزدوج مع استمرار التحقق من صحة `plan/stage.json`:

#### محرك `P` (`scenes.py`)
```python
from stage import create_stage, render_fixed_stage

STAGE = create_stage(STAGE_SPEC)

def render_frame(t: float):
    return render_fixed_stage(
        STAGE["spec"],
        t,
        lambda ts, state: render_scene_content(ts, state["win"]),
        duration=TOTAL_VO_SECONDS,
        direction=DIRECTION,
        copy_by_id=COPY_BY_ID,
        words=MEASURED_WORDS,
        caption_style="pop",
    )
```

#### محرك `K` (`src/scenes/s1.js`)
```js
import { renderFixedStage } from '../lib/stage-canvas.js';

export const manualFixedStage = true;

export async function draw(ctx, localT, { t, dur, direction }) {
  await renderFixedStage(ctx, STAGE_SPEC, t, {
    duration: TOTAL_VO_SECONDS,
    direction,
    copyById: COPY_BY_ID,
    drawContent: (c, state) => drawSceneBody(c, localT, state.win),
  });
}
```

#### محرك `R` (`RemotionRoot.tsx`)
```tsx
import {FixedStage} from './lib/FixedStage';

<FixedStage
  spec={STAGE_SPEC}
  time={frame / fps}
  duration={durationInFrames / fps}
  direction={DIRECTION}
  copyById={COPY_BY_ID}
  over={<CaptionOverlay time={frame / fps} />}
>
  {(state) => <SceneContent time={frame / fps} win={state.win} />}
</FixedStage>
```

---

## ٨) الحدود المعروفة (Known Limitations — نطاق Phase 2A فقط)

1. يغطي هذا النظام **Phase 2A (Fixed Stage)** فقط؛ لا يتضمن جدار الشرائح ثلاثي الأبعاد (3D Slide Wall) أو تحليق الكاميرا بين البطاقات أو انتقالات One-Take أو تحريك المؤشر التفاعلي.
2. لا يضيف النظام أي اعتمادية على Three.js أو أي حزمة خارجية جديدة.
3. يعتمد الفحص `L06` على صناديق الحبر المحافظة (Screen-space ink AABBs لكل سطر نصي)؛ وهو يكتشف بدقة دخول السطر النصي في منطقة القطع الدائري للزاوية، لكنه لا يغني عن المراجعة البصرية لشكل الحرف العربي.
