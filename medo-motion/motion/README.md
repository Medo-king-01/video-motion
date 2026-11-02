# motion — لغة الحركة الموحّدة

> منحنيات motion.dev + نموذج تأليف Theatre.js، من غير مكتباتهم وقت الرندر.
> الريل بيتصدّر فريم فريم، فأي حاجة هنا **دالة في الزمن**: نفس الفريم دايمًا نفس الشكل.

| الملف | إيه ده |
|---|---|
| `easings.json` | ١٢ cubic-bezier بأسماء motion.dev + ٥ spring presets + توقيتات البراند (المصدر الوحيد) |
| `text-animations.json` | كتالوج ٥١ حركة نص (ريلز) كمسارات `{t,v,ease}` + مقدمات كابشن آمنة — `docs/text-animations.md` |
| `examples/card-entrance.json` | تايملاين جاهز للتجربة |
| `../templates/render/lib/motion.js` | المحرك K: `ease` · `spring` · `keyframes` · `timeline` · `stagger` · `reveal` |
| `../templates/procedural-reels/motion.py` | المحرك P: نفس الـAPI بالحرف |
| `../templates/render/lib/captions.js` | كابشن كلمة-كلمة بـ`style` **مطلوب** يختاره الوكيل لكل مشهد (`plan/text-direction.json`) — بتوقيت مقاس، من غير default |

```js
import { timeline } from './lib/motion.js';
const tl = timeline({ duration: 2, tracks: { 'card.y': [{t:0,v:240},{t:.7,v:0,ease:'spring'}] } });
const v = tl.at(0.4);       // v['card.y']
```

```python
from motion import timeline
v = timeline({"tracks": {"card.y": [{"t": 0, "v": 240}, {"t": .7, "v": 0, "ease": "spring"}]}}).at(0.4)
```

- التأليف بالعين: `python3 -m http.server 8080` ثم `http://localhost:8080/tools/motion_studio.html`.
- التأليف في Theatre.js: `python3 tools/theatre_import.py state.json --offset 18.5`.
- الشرح الكامل والوصفات: `docs/motion.md`. الاختبارات: `tests/test_motion.py` (بتقارن JS وPython رقميًا).
