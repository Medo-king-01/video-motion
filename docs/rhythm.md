# الإيقاع والفضاء — Rhythm & space

ملاحظات مهارة «مصمّم موشن برمجي» (١٥ ثانية، HTML/Canvas، `seek(t)`) اتاخد منها اللي بينفع في الاستوديو
ده، واتساب اللي ما ينفعش. القاعدة اللي بنيت عليها: **كل حاجة دالة نقية في الزمن `t`** — عندنا أصلًا
كده في المحركين (`renderFrame(t)` / `draw(fr, t)`)، والجديد هنا هو **الإيقاع** و**الفضاء** و**الـblur**.

## اللي اتاخد فعلًا | Adopted (working code, both engines)

| الفكرة | عندنا |
|---|---|
| محرك زمني حتمي `seek(t)`، بدون CSS/timers/state | كان موجود؛ دلوقتي في تست (`test_rhythm` + `test_space3d`): نفس `t` مرتين = نفس البكسلات |
| الإيقاع بيحكم الميكرو-حركة والقطع (120 BPM) | **`beat.py` / `lib/beat.js`**: `grid`, `quantize`, `ping`, `swell`, `ladder`, `on_grid`, `snap_bounds` |
| القطع على الشبكة مش على الإحساس | **`vo_length.py --bpm 120`**: بيزحزح نقط القطع لأقرب ضربة (بفارق ≤ `--snap-tol`)، وبدون ما يغيّر طول الـVO |
| أصوات على الشبكة | **`sfx.grid_cues("k.h.|k.h.")`** حرف لكل ١/١٦، و`make grid` بيكتب cue sheet جاهز للميكس |
| تحويل مستمر بدل القطع (metamorphosis) | **`space3d.py` / `lib/space3d.js`**: مش مجرد قطع — العنصر بيلف/يتعمّق ويتحوّل للتكوين اللي بعده |
| إسقاط 2D→3D + extrude | نفس الموديول: `box`, `prism`, `camera`, `project`, `sorted_faces` (painter's)، `shade` |
| Motion blur بالسرعة | **`motion.blur_steps` / `drawBlurred`**: `displacement = v · shutter`، الأوزان مجموعها ١ (التعرّض ثابت) |
| «صفر لمسات عشوائية» | القائمة البنيها في `TASTE.md` (لا particles/lens flare/camera shake/RGB split/crossfade عشوائي) |

## اللي رفضناه | Deliberately not adopted

| في المهارة | ليه لأ |
|---|---|
| بالِت ٣ ألوان + أسود/أبيض | البراند مقفول على ١٢ لون (`brand.json`). بناخد **الانضباط** مش الأرقام: المشهد بيستخدم ٢–٣ ألوان من البالِت + محايدين |
| ١٩٢٠×١٠٨٠ أفقي | الشغل ١٠٨٠×١٩٢٠ راسي ٣٠fps، والـsafe zones من `brand.json` |
| خط Inter/Geist | Cairo مقفول للعربي |
| Web Audio API للتوليد | الرندر أوفلاين: `sfx.py` (numpy، seed ثابت) بيطلع نفس الصوت كل مرة، و`mix.py` بيخلطه مع الـVO على −14.5 LUFS |
| «مفيش hold أطول من ٠.٥ ث» | قاعدة صارمة أوي لريل فيه كلام: عندنا **لا ساكن > 2.5 ث** (`brand.json`)، وبنفضل حركة صغيرة مستمرة |
| «crossfade ممنوع» كقاعدة مطلقة | الـcrossfade بين الوضعيات مش crossfade مونتاج: هو **شكل الانتقال** في `presenter.py` (شكله مقصوص، مش dissolve) |
| `bounce/elastic` ممنوعين | موجودين في `easings.json` لكن للتفاصيل الصغيرة بس — الحركة الكبيرة `expo/circOut` (`docs/motion.md`) |

## ١. الإيقاع | The beat grid

```python
from beat import grid, quantize, ping, swell, on_grid
g = grid(t, 120)            # {'beat', 'phase', 'bar', 'bar_phase', 'pos', 'spb'}
x = quantize(1.44, 120, 2)  # 1.5 — ثُمن
k = ping(t, 120, curve=14)  # 1 على الضربة → ~0 قبل اللي بعدها
title = 0.9 + 0.1 * ping(t, 120)     # نبضة مقياس صغيرة، مش bounce
stagger = on_grid(4, 120, 4)         # 0, .125, .25, .375
```
```js
import { grid, quantize, ping, onGrid } from './beat.js';
const scale = 1 + 0.16 * ping(t, 120, 0, 9);
```

- **BPM واحد** للريل كله (أو للفصل الواحد) — بيتحدد من موسيقى/إيقاع الكلام، مش عشوائي.
- القطع اللي مش على الشبكة بتتحس كغلطة حتى لو محدش عارف يسمّيها.
- `snap_bounds` بيحرّك **نقط القطع الداخلية بس**؛ أول وآخر نقطة ملك الـVO، مش الشبكة.

## ٢. الفضاء | Turns instead of cuts

```python
from space3d import prism, camera, draw_mesh, transform
card = prism([(-160, -220), (160, -220), (160, 220), (-160, 220)], 60)
cam   = camera(dist=1500, yaw=0.55, pitch=-0.12, fov=38)
draw_mesh(draw, transform(card, ry=0.5 + 0.3 * t),
          cam, W, H, {"front": "#CB271B", "side": "#9F0803"}, outline="#030303")
```
- `+x` يمين، `+y` فوق، `+z` ناحية المشاهد. الشاشة y لتحت — التحويل جوه `project`.
- **cull** بيشيل الأوجه اللي بتبص بعيد (صح للمجسمات المقفولة، غلط للشرائط).
- الإسقاط perspective: نفس العنصر بعيد = أصغر، فالتكوين ممكن يتغيّر من غير قطع.
- متستخدمهاش لعنصر واحد — **طبقتين بعمق مختلف** (الأمامية + شبح ورا) هما اللي بيعملوا إحساس بالمساحة.

## ٣. الـblur | Velocity, not a filter

```python
from motion import velocity, blur_steps
vx = velocity(lambda t: cx(t), t)          # px/s
steps = blur_steps(vx, 0, samples=6, shutter=0.055, max_px=26)   # [(dx, dy, w), …]
# كل step: ارسم العنصر بإزاحة وألفا مضروبة في w
```
- `shutter` = التعرّض الافتراضي (ثانية). الإزاحة = السرعة × التعرّض بإقصى حد `max_px`.
- الأوزان متساوية ومجموعها ١ → الألوان والتعرّض ما يتغيّروش.
- سرعة صفر → خطوة واحدة `(0, 0, 1)` = رسم عادي حاد (مفيش تكلفة).
- في K: `drawBlurred(ctx, c => c.fillText(…), vx, 0, {samples: 5, shutter: 0.06})`.

## ٤. عرض حي | Live demo

`medo-motion/templates/render/scenes/kinetic-example.js` (٣١.٤–٣٥.٤ ث في ريل الديمو): صفحة حمراء
مُعمّقة بتلف مع الإيقاع + كلمة عربية بتتزحلق وتتبلر بسرعتها الحقيقية + قراءات `beat/phase/velocity`
على الشاشة. جرّبه: `node src/render.js --from 31.45 --to 35.35 --fps 4 --scale .35 --out cache/k --jpg`.

## ٥. قبل ما تسلّم | Checks

- [ ] الريل بطول الـVO (`vo_length.py --check`) وفي نفس الوقت القطع على الشبكة (`--bpm`).
- [ ] كل حركة دالة نقية في `t` — شغّل نفس الفريم مرتين وتساوي.
- [ ] مفيش ساكن > 2.5 ث، ومفيش عنصر بيلف لحد ما يختفي (تقاطع edge-on قذر).
- [ ] الـblur بيحصل عند السرعة بس؛ العنصر الساكن حاد.
- [ ] مفيش لون برّه البالِت (`brand_check.py`).
