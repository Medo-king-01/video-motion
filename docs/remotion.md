# محرك R — Remotion + React/TypeScript

محرك ثالث اختياري للريلز اللي هتستفيد فعلًا من مكوّنات React القابلة لإعادة الاستخدام، الرسوم المبنية من بيانات، أو مراجعة الـtimeline في Remotion Studio. **مش بديل تلقائي للمحرك K**؛ الاتنين بيرندروا من Chromium، واختيار R مش معناه إنه أسرع.

## إنشاء مشروع وتجربته

```bash
bash tools/setup.sh                 # مرة على الجهاز: يجهّز Chromium المشترك
python3 tools/new_project.py my-reel --engine r
cd projects/my-reel
npm ci                              # الحزم مثبتة في package-lock.json
npm run typecheck
npm run studio
```

القالب بيوفّر Composition طولها من `plan/beats.json`. لو الملف لسه من غير مدة مقاسة، Studio بيعرض معاينة قصيرة عليها علامة `PREVIEW`، لكن الرندر الكامل بيتوقف عمدًا لحد ما يتقاس الصوت وتتحط حدود المشاهد:

```bash
python3 ../../tools/vo_length.py out/vo24.wav --json plan/beats.json
# جهّز out/vo24.wav حسب خطوات AGENTS.md، وبعدها من جذر المشروع:
npm run stills                 # 4 review frames by default
npm run stills -- 3 7.5        # exact review times in seconds
npm run render -- --audio out/vo24.wav
```

`render` بيتأكد إن المدة وFPS وحدود المشاهد متوافقة، وإن ملف الصوت PCM WAV ومدته مطابقة للتوقيت، وبعدها بيضم التعليق للصورة. `--silent` متاح لاختبار بصري فقط، مش لتسليم فيديو نهائي. بعد الرندر، لسه لازم تعدّي مراحل فحص/ماستر الصوت ومعايير التسليم في `AGENTS.md`.

## إيه اللي بيتشارك مع الاستوديو

- مقاس 1080×1920 و30fps، ونسخة `src/brand.ts` مربوطة بفحص `brand_check.py`.
- Cairo محلي في `public/fonts/` لتشكيل عربي ثابت؛ مفيش اعتماد على Google Fonts أثناء الرندر.
- مكتبة وضعيات ميدو في `public/assets/poses/` ومكوّن `MedoPresenter` للصور الشفافة والحركة الحتمية الخفيفة.
- نفس `plan/beats.json` الناتج من `tools/vo_length.py`، ونفس ملف `lib/motion.js` المستخدم في K؛ اختبار الحركة بيتأكد إن النسختين متطابقتين.
- كود الفيديو بيتحدد من رقم الفريم بـ`useCurrentFrame()`؛ ممنوع CSS animation أو `Math.random()` أو state زمني بين الفريمات.

## حدود النسخة الحالية

- R مناسب للمكوّنات والـcompositions، لكن كتالوج الأيقونات المتحركة والانتقالات المربوطة بمؤثراتها ما زال wired لمحركَي P وK؛ ما تدّعيش إن كل primitive من P/K متاح في R قبل port واختباره.
- مشاهد Remotion بتتنسخ لمجلد المشروع؛ عدّل نسخة المشروع، مش `medo-motion/templates/remotion/`.
- الحزم مثبتة بإصدارات محددة في `package.json` و`package-lock.json`. **zod:** Remotion 4.0.539
  بيطلب `4.5.4` بالظبط (`extraPackages` في `@remotion/studio-shared`)، و`4.5.4` نفسها عندها advisory
  عالي (استهلاك ذاكرة عند التحقق من مجموعات مقيدة ضخمة). القرار: `overrides: {"zod": "^4.6.7"}`،
  والثمن تحذير Remotion المتوقع `zod: installed 4.6.7, required 4.5.4` في كل رندر.
  **مقاس في الاتجاهين على نفس القالب** (`npm ci` ثم `npm audit` و`npx remotion versions`):

  | | `npm audit` | `npx remotion versions` |
  |---|---|---|
  | مع الـoverride (`^4.6.7`) | **0 vulnerabilities** | `zod: installed 4.6.7, required 4.5.4` |
  | بدون الـoverride (4.5.4) | **10 high** (zod + 9 حزم Remotion) | `All packages have the correct version.` |

  يعني إزالة الـoverride بتشيل التحذير وتفتح الـadvisory. التحذير مقبول ومقصود، ومحروس
  بـ`tests/test_remotion_skill.py` (الـoverride موجود، والـlock فعلاً بيحل zod ≥ 4.6.7).
  يُعاد النظر لما Remotion يطلب نسخة zod مصلَّحة. اختبارات typecheck/stills/render شغالة على
  الحالتين. `node_modules/` ومخرجات الرندر مش بتدخل Git.
- سكربتات R بتستخدم Chromium المشترك من `tools/setup.sh` عشان ما تعتمدش على تنزيل متصفح من `remotion.media`.
- Remotion وتبعياته لها شروط ترخيص مستقلة عن ترخيص هذا المستودع؛ راجعها قبل الاستخدام التجاري أو التوزيع.
