# كتالوج الحركة التنفيذي — ما يُشتغَّل فعلًا وما هو وصف

**التاريخ:** 2026-11-12 · **الملف:** `medo-motion/motion/moves.json` · **الفاحص:** `tools/moves.py`

هذا الملف يجيب سؤالًا واحدًا بدقة: **كم حركة يستطيع الاستوديو تشغيلها فعلًا؟** الجواب ليس عدد
مدخلات مكتبة التقنيات. المكتبة الوصفية <!-- AUTO:techniques -->2,239<!-- /AUTO --> مدخلًا ليست بنك
حركات: حقولها نصوص (`summary` · `how` · `use_when`) وتصنيف `primitive` من عشر فئات، ولا اسم دالة
فيها. **(58 مدخلًا فقط يحمل `evidence`.)**

## 1. الحالة المقاسة الآن

| العائلة | الوحدة | العدد | P | K | R | Hybrid |
|---|---|---:|---|---|---|---|
| `caption-entrances` | مدخل نص | 51 | ✓ | ✓ | ✓ | — |
| `element-effects` | مؤثر عنصر | 3 | ✓ | ✓ | مشروط | — |
| `transitions` | انتقال مشهد | 14 | ✓ | ✓ | ✗ | — |
| `element-moves` | حركة عنصر | 10 | ✓ | مشروط | مشروط | — |
| `techniques-library` | وصف | 2,239 | **وصفي — ليس حركة** | | | |

**الإجمالي التنفيذي: 78** (منها 10 حركات عنصر جديدة في B1ب). يُطبع بالأمر:

```bash
python3 tools/moves.py --audit
```

الأرقام مولّدة من المصادر نفسها (`moves.measure`) ولا تُكتب هنا يدويًا؛ تغيير الملف الأصلي يكسر
الاختبار إن لم يُحدَّث السجل.

## 2. معنى «تنفيذي» في هذا المستودع

العائلة `executable` فقط إذا:

1. **مصدر** موجود فعليًا (ملف JSON أو وثيقة تُعرّف الوحدة).
2. **تنفيذ** لكل محرك مدعوم: مسار ملف + رموز (`symbols`) موجودة **نصًّا** في الملف.
3. **دليل**: اختبار أو قائمة اختبارات موجودة.
4. `conditional` يحمل شرطه مكتوبًا، و`unsupported` لا يدّعي شيئًا.
5. `preview` موجود لكل عائلة تنفيذية (وثيقة أو شيت مراجعة).

العائلة `descriptive` يجب أن تكون **بلا محركات** وأن تحمل `why` — وهذا ما يمنع عودة الخطأ القديم:
«عندنا 2,239 حركة».

## 3. الرموز الحالية (مرجع سريع)

| العائلة | K | P | R |
|---|---|---|---|
| مداخل النص | `render/lib/caption-motion.js` · `captionTransform` | `procedural-reels/caption_motion.py` · `caption_transform` | `remotion/src/lib/caption-motion.js` |
| مؤثرات العنصر | `render/lib/effects.js` · `lightSweep`/`whipPan`/`particleDissolve` | `procedural-reels/effects.py` | مشتركة لكن بلا استهلاك تلقائي في R |
| الانتقالات | `render/lib/transition.js` · `transitionLayer`/`compositeTransition` | `procedural-reels/transition.py` · `composite` | غير مدعومة |
| حركات العنصر (B1ب) | `render/lib/moves-render.js` · 10 دوال `draw*` | `procedural-reels/moves.py` (نقية، بلا محوّل رسم) | `src/lib/moves.js` (نقية، بلا مكوّن يستهلكها) |

`Hybrid` لا يملك عائلة خاصة: يستخدم عائلة المحرك الذي يرسم الطبقة. أي عائلة جديدة تدّعي Hybrid
تحتاج تنفيذًا صريحًا، لا وراثة ضمنية.

## 4. إضافة عائلة جديدة (العقد)

```json
"my-family": {
  "title": "…",
  "state": "executable",
  "source": "path/to/source.json",
  "sourceCollection": "items",
  "count": 12,
  "unit": "element move",
  "timing": "نافذة زمنية صريحة…",
  "preview": "docs/…",
  "limits": ["…"],
  "engines": {
    "K": {"state": "supported", "impl": "medo-motion/templates/render/lib/x.js",
          "symbols": ["applyX"], "evidence": ["tests/test_x.py"]}
  }
}
```

ثم: `python3 tools/moves.py --check` يجب أن يمرّ. إن لم يمرّ فالعائلة غير جاهزة، وليست «قريبة».

**ما لا يفعله هذا الملف:** لا يرندر شيئًا، ولا يضيف حركة. إضافة الحركة نفسها تبقى عملًا في المحرك
مع اختبار إطار. السجل يمنع الادّعاء فقط.

## 5. عائلة B1ب: عشر حركات عنصر جديدة

كل حركة **دالة نقية** (JS في `shared/js/moves.js` + مرآة Python) و**محوّل رسم** في K، بلا عشوائية
وبلا حالة داخلية:

| الحركة | الدالة | ما تضمن |
|---|---|---|
| `pixel-list` | `pixelListItem` / `pixel_list_item` | أسطر تدخل بعد `stagger`، والإزاحة منقّطة على بكسل حسب حجم الخط |
| `parallax` | `parallaxLayer` / `parallax_layer` | عمق 0 مثبّت، عمق 1 يتبع الكاميرا، تكبير محدود |
| `orbit` | `orbitItem` / `orbit_item` | دوران على قطع ناقص؛ العمق يغيّر الحجم والترتيب |
| `word-path` | `wordPathItem` / `word_path_item` | كلمة تسير على مسار مستقيم وتستقر |
| `explode` | `explodePart` / `explode_part` | تفكيك شعاعي ثم إعادة تجميع (فتح/ثبات/رجوع) |
| `mask-wipe` | `maskWipe` / `mask_wipe` | مستطيل قصّ متحرك بأربعة اتجاهات |
| `data-count` | `dataCount` / `data_count` | عدّاد رقمي حتمي بكسور عشرية محدودة |
| `card-stack` | `cardStackItem` / `card_stack_item` | كروت متراكبة تدخل بالتتابع |
| `camera-push` | `cameraPush` / `camera_push` | دفع/تحريك كاميرا حول مركز الإطار |
| `particle-burst` | `particleBurst` / `particle_burst` | شظايا بجاذبية، بتجزئة عدد صحيح مشتركة مع P |

- المحوّلات: `drawPixelList` · `drawParallax` · `drawOrbit` · `drawWordPath` · `drawExplode` ·
  `drawMaskWipe` · `drawCardStack` · `drawCameraPush` · `drawParticleBurst` · `drawDataCount`.
- التكافؤ K/R بايتًا ببايت، والتكافؤ مع P رقميًا على شبكة عينات — `tests/test_moves_b1b.py` (37 اختبارًا).
- **المعاينة:**

```bash
node tools/moves_preview.mjs out/moves.html   # 40 إطارًا SVG، مخرَج ثابت بايتًا
```

**الحدود المعلنة:** P وR يملكان الدوال النقية فقط بلا محوّل رسم (لذلك `conditional`)؛ `word-path`
مستقيم فقط؛ `mask-wipe` يرسم حدًّا حادًا و`feather` معلن غير منفّذ؛ `pixel-list` تنقيط إزاحة لا فسيفساء؛
البارالاكس يحتاج ترتيب طبقات صريحًا من المشهد.

## 6. الخطوة التالية

B1ب مكتملة (10/10) و**B2 مكتملة** — [`board.md`](board.md): عقد `board.json` + مُفسِّر `shared/js/board.js`
(ستة أنواع عناصر) + مدقّق `tools/board_check.py` + معاينة SVG. الحركات العشر صارت لبنات تركّبها اللوحة
بلا كود مشهد. و**B3 مكتملة** — [`explode.md`](explode.md): فكّ/تجميع حتمي فوق `machine-kit.js`.
و**B4 مكتملة** — [`cut-plan.md`](cut-plan.md) — و**B5 مكتملة** — [`timeline.md`](timeline.md).
التالي: **B6 ✅ منفّذ** — [`profiles.md`](profiles.md) و[`subtitles.md`](subtitles.md). ملاحظة:
معدل العرض والترجمة ليسا حركة؛ لا يُضاف أي منهما إلى كتالوج `moves.json`.
