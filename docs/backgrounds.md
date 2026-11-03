# الخلفيات المتحركة — Animated backgrounds

## اللي عندنا | What ships
**١٢ نمط × ثيمين (dark/light) = ٢٤ خلفية**، كلهم بالپاليت بتاع البراند، وكلهم **دالة نقية للزمن**:
فريم `t` بيتحسب من الصفر، فالفريم ١٣٧ هو نفسه سواء الرندر ماشي للأمام أو نطّ أو رندر chunks
بالتوازي. مفيش حالة متجمّعة، مفيش CSS animation، مفيش requestAnimationFrame جوه المحرك.

| id | الاسم | العائلة | الاستخدام |
|---|---|---|---|
| `iso-grid` | شبكة مائلة | grid | أهدأ خلفية للشرح والتفسير |
| `grid-2d` | شبكة مستقيمة | grid | إحساس «نيون» بالبراند من غير نيون |
| `paper` | ورق مجعّد | texture | مواضيع ورقية/تعليمية/مستندات |
| `aura` | أورا ناعمة | gradient | الكلام الهادي، لحظات التأمل |
| `orbital` | مدارات | orbit | التقنية والمنتجات والـSaaS |
| `orbit-mono` | مدارات رمادية | orbit | الحياد التام (بدون أحمر) |
| `frames` | واجهة تقنية | frames | الداتا والتحليلات والـdashboard |
| `organic` | شبكة ماسية | texture | إحساس هادي وطبيعي |
| `perspective` | منظور | perspective | السرعة، التقدم، «الطريق قدام» |
| `glyphs` | حروف ساقطة | texture | التحول الرقمي (حروف عربية وأرقام — مش كاتاكانا) |
| `pulse` | نبض | signal | النتائج والأرقام و«قبل/بعد» |
| `wash` | تدرج ناعم | gradient | الافتراضي لو مفيش سبب لغيرها |

المصدر البصري: مكتبة أرسلها صاحب البراند (١٢ نمط × فاتح/غامق). الهندسة اتحفظت، والألوان اتحوّلت
كلها لرموز براند. الأنماط اللي كانت خارج الپاليت اتحوّلت مش اتشالت: `matrix` (كاتاكانا) بقى
`glyphs` بحروف عربية، `pulse` (أخضر ECG) بقى أحمر البراند، `pastel` (بنفسجي) بقى `aura`
بـ`blush`+`red_deep`، و`crimson` اندمج في `grid-2d` بدل ما يبقى أحمر تاني مختلف عن `#CB271B`.

## قاعدة الألوان | Colour rule
مفيش **hex** جوّه أي نمط. كل خلفية بتطلب **دور براند** (role)، والدور بيتحوّل لـtoken من
`brand/brand.json`:

```json
"dark":  { "bg": "ink", "line": "gray_1@0.10", "accent": "red", "accentSoft": "salmon@0.30" }
"light": { "bg": "paper", "line": "ink@0.09", "accent": "red_deep", "accentSoft": "red_deep@0.20" }
```

`token@alpha` = نفس اللون بشفافية. **ممنوع** أي لون خارج الپاليت — `tests/test_backgrounds.py`
بيفحص كل بكسل: لازم يكون على الخط بين لونين براند (يعني mix مسموح، hue غريب مرفوض).

## الاستخدام | Usage
```python
# engine P
from backgrounds import frame, paint_into
bg = frame("pulse", 1080, 1920, t=2.4, theme="dark")     # (1920,1080,3) uint8
paint_into(canvas, "wash", t=2.4, theme="light")          # في المكان
```
```js
// engine K + R (same file)
import { backgroundFrame, paintBackground } from '../lib/backgrounds.js';
backgroundFrame(ctx, 1080, 1920, t, { id: 'frames', theme: 'dark' });
paintBackground(canvasEl, t, { id: 'orbital', theme: 'light' });   // بيظبط DPR لوحده
```
- **مفيش خلفية افتراضية في السين**: لو المشهد محتاج خلفية، اختار واحدة بالاسم وقول ليه في
  `plan/design.json`. الشيت بيوريك الاتنين قبل ما تقرر.
- عدّل `density` / `angle` / `speed` لكل مشهد — القيم الافتراضية في الكتالوج والزيادة عليها مسموحة.
- `contrastSafe: false` في الكتالوج = تحت النص المفتوح ممكن تحتاج طبقة تعتيم 20–30%.

## المراجعة | Review sheet
```bash
python3 tools/backgrounds_sheet.py                  # كل الأنماط، الثيمين، بمحرك P
python3 tools/backgrounds_sheet.py --only pulse,wash --theme dark
python3 tools/backgrounds_sheet.py --compare         # P | K | فرق لكل نمط
make backgrounds
```
`--compare` بيرندر نفس الفريم في **K** (Canvas حقيقي في Chromium) جنب **P** وبيطبع `Δ` لكل نمط.
الاختبار بيفشل لو أي نمط زاد عن **Δ16** متوسط، والواقع حاليًا: كل الـ٢٤ تحت **Δ11**.

## التكافؤ | Parity
| الملف | بيخدم |
|---|---|
| `medo-motion/motion/backgrounds.json` | الكتالوج (ids, roles, params) — مصدر الحقيقة |
| `medo-motion/templates/render/lib/backgrounds.js` | **K و R** (نفس الملف بايت-بايت) |
| `medo-motion/templates/procedural-reels/backgrounds.py` | **P** (نسخة numpy) |
| `tools/backgrounds_sheet.py` | الشيت + فحص التكافؤ |

**كلفة حقيقية:** أي نمط جديد = تنفيذين (JS + Python) + اختبار. الـJS واحد لـK/R، لكن P محتاج نسخة.

## أخطاء اتعلمناها | Gotchas
- **Canvas بيعمل fade لـ«transparent» = أسود شفاف**، فالـgradient بيغمق في النص. الحل: `fadeOut()`
  بيرجّع نفس اللون بـalpha 0 (اللون مش الأسود). ده كان بيبان كبقعة رمادية في عمود K.
- **مقاييس الماسك في P** بتتحسب على نص الدقة (`MASK_SCALE=2`) وبتتكبر — التدرجات الناعمة مش
  بتخسر حاجة، والفريم بينزل من ٤٠٠ms لـ١٠٠ms.
- **`glyphs` مش بيعيد بناء الـPIL لكل حرف** — طبقة RGBA واحدة + `alpha_composite` (كان ٣٢٨ms → ٤٥ms).
- **`pulse` متجه بالكامل** — حلقة بيكسل على ارتفاع الفريم كانت ٤٦٧ms → ٤٠ms.
- الفريم الكامل 1080×1920 لكل الأنماط ≈ **٢.٥ ثانية** إجمالًا (متوسط ~٢٠٠ms/نمط) على جهاز CI.

## إضافة نمط | Adding a background
1. ضيف الـid والـroles والـparams في `motion/backgrounds.json`.
2. اكتب الـpainter في الملفين بنفس الرياضيات (`PAINT` في الـJS، `PAINTERS` في الـPython).
3. `python3 tools/backgrounds_sheet.py --compare --only <id>` — شوف الفرق، لازم يبقى تحت ١٦.
4. `python3 -m pytest tests/test_backgrounds.py`.
