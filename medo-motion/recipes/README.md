# medo-motion/recipes — وصفات المشاهد | Scene Recipes

**الحالة:** قرار تسجيل (2026-11-09) · يكمل «Looks مقفولة» بخطوة زيادة: من «اللقطة دي شكلها إيه؟»
لسؤال العمل «لمشهد زي ده أعمل إيه؟».

ملف واحد: `recipes.json` — **8 وصفات جاهزة**، كل واحدة بتسمّي: المحرك المفضّل (+ بدائل مثبتة)،
ملفات `plan/` المطلوبة (نسبة للمشروع)، الأدوات اللي بتفحصها، الـLooks المناسبة، والحركات
المميزة. الوصفات منسقة مع عقود الاستوديو نفسها — ملهاش قول فوق الـlint ولا فوق الـgates.

```json
{"recipe": "tech-demo-ui"}
```

## الوصفات (2026-11-09)

| id | المشهد | المحرك | الـLooks المناسبة |
|---|---|---|---|
| `tech-demo-ui` | شاشة منتج تتفاعل (نافذة/مؤشر/clicks) | K (+P/R) | tech-dark, house |
| `machine-explainer` | قطعة هارد بمصدر فعلي (X01–X04) | P (+K) | tech-dark, explain-paper |
| `kinetic-hook` | هوك تايبوغرافي / رقم صاخب | K (+P) | kinetic-hook, house |
| `list-steps` | قائمة/خطوات مرقمة (3–6 بنود) | K (+P/R) | swiss-data, explain-paper |
| `counter-proof` | رقم/مقارنة موثقة بمصدر أو disclaimer | R (+K) | swiss-data, tech-dark |
| `one-take` | لقطة واحدة مستمرة (`plan/one-take.json`) | P (+K/R) | tech-dark, house |
| `slide-wall` | حائط شرائح 3D (`plan/slide-wall.json`) | K (+P/R) | house, kinetic-hook |
| `presenter-overlay` | ميدو بيتكلم + عناصر فوقه (beat-by-beat) | P | warm-story, house |

## القواعد

- **موديل ضعيف:** قول `recipe: "<id>"` وسيب الـengine hint والملفات المطلوبة تقادك.
- **موديل قوي:** الوصفة شيك ليست، مش قيد — بس كل ملف في `requires` مطلوب، وكل validator
  في `validators` لازم يعدّي قبل الرندر.
- `engines[0]` هو المفضّل، الباقي بدائل مثبتة. **Hybrid** قرار pipeline مش وصفة مشهد.
- `ui: true` = نفس `"ui": true` في مشهد `plan/beats.json` — الشاشة لازم تتغير (lint `U01`).
- الـLooks توصيات — أي look من `medo-motion/looks/looks.json` صالح.
- `requires` والملفات المسماة مش خيال: أي ملف أو مسار validator اسمه غير موجود في الريف
  بيكسر `tests/test_recipes.py`.

## الأدلة

- `python3 -m pytest tests/test_recipes.py`
- الوصفة بتتقفل على مانيفستات الاستوديو: الـtechniques موجودة في `assets/techniques.json`،
  والـLooks موجودة في `medo-motion/looks/looks.json`، والـvalidators والـdocs موجودة في الريف.
- مشهد مش في القائمة؟ اكتب وصفته هنا بدل ما ترتجل — أو روح بالاختيار الصريح ولودها لفيلم.
