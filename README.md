# video-motion — استوديو ريلز ميدو 🎬

مستودع واحد فيه كل حاجة لصناعة **ريلز عمودي 1080×1920** من أوله لآخره:
الهوية مقفولة (بالِت ١٢ لون + Cairo)، ومحركين رندر، وطبقة أيقونات متحركة، وأدوات صوت، وقواعد عربي سليم،
وكل ده شغال مع **أي وكيل برمجي** — مش كلود بس.

---

## إزاي بتشتغل

إنت بتدّي **٤ حاجات** بس:

| # | الحاجة |
|---|---|
| ١ | **السكريبت** (يفضل beats مرقمة + اللي يظهر على الشاشة) |
| ٢ | **توجيه المشاهد** (إزاي عايز المشاهد تتقدم) |
| ٣ | **صوت التعليق** (تسجيلك) |
| ٤ | **صور ميدو** (٢–٤ وضعيات) |

والباقي كله على الوكيل: الخلفيات والكروت والأجهزة والكابشن والحركة والمؤثرات والموسيقى
والتوقيت وأي أصل خارجي (كود ← توليد AI ← بحث) مع تسجيل التراخيص.

**مفيش لوجو، مفيش اسم سلسلة، مفيش رقم حلقة.** ده استوديو: إنت بتقول عايز إيه.

---

## أول تشغيل

```bash
bash tools/setup.sh        # بينزّل اللي ناقص (python deps · ffmpeg · خطوط · كروميوم)
python3 tools/doctor.py    # تقرير READY / DEGRADED / BLOCKED لكل قدرة
python3 tools/selftest.py  # فحص كامل: doctor + اختبارات + رندر حقيقي من المحركين
```

أو باختصار: `make setup` · `make doctor` · `make selftest` · `make test` · `make new SLUG=اسم`

مشروع جديد:

```bash
python3 tools/new_project.py اسم-المشروع --engine p   # محرك الشخصية/الشرح (الأنسب للريلز اللي فيها كلام)
python3 tools/new_project.py اسم-المشروع --engine k   # محرك كانفس/تايبوغرافي
```

بعدها املأ `projects/<المشروع>/BRIEF.md` بالأربعة، وقول للوكيل: **«اقرأ AGENTS.md وابدأ»**.

---

## اللي جوه

```
AGENTS.md              ← عقد التشغيل لأي وكيل (اقرأه الأول)
assets/                ← مدخلات مشتركة: fonts/Cairo · poses/ · sfx/
projects/<slug>/       ← كل فيديو: BRIEF.md · plan/ · assets/ · out/ · PROGRESS.md
tools/                 ← setup.sh · doctor.py · selftest.py · new_project.py · ffprobe_shim.py · chromium.mjs
                         · icons_sheet.py (مراجعة الأيقونات) · icons_preview.mjs
tests/                 ← اختبارات pytest (تشكيل عربي، البراند، السكافولد، فريم حقيقي)
docs/                  ← التحليل + قواعد الاتساق
medo-motion/           ← الحزمة (النسخة الخاصة من «موشن خام» v1.4.1)
  SKILL.md             ← نقطة دخول كلود كود (بتحوّل لـ AGENTS.md)
  brand/               ← الهوية: BRAND.md للبني آدم + brand.json للكود
  reference/           ← أدلة تُقرأ عند الحاجة (العربي إلزامي قبل أي نص على الشاشة)
  icons/              ← ٢٧٥ أيقونة متحركة (١٢ بيت + ٢٦٣ من itshover): registry → SVG + محرك K + محرك P
  styles/               ← ٩ ستايلات إلهام، والافتراضي medo-red-circle
  templates/           ← محرك P (Pillow/OpenCV/FFmpeg) + محرك K (Canvas/Playwright)
  scripts/             ← preflight · brand_check · get_fonts · SFX · TTS · preview
```

---

## المحركات

| | إمتى تستخدمه | بيشتغل إزاي |
|---|---|---|
| **P** | ريلز فيها ميدو + كروت + أجهزة + كابشن | Pillow + OpenCV، رندر بالـchunks (قابل للاستئناف) |
| **K** | تايبوغرافي حركي، قوائم، واجهات، مشاهد تقيلة | Canvas في Chromium (Playwright) |

محرك واحد للفيديو الواحد، ونفس البالِت من `brand/brand.json`.
الأيقونات مشتركة بينهم: `medo-motion/icons/` → `lib/icons.js` (K) + `icons.py` (P) + `svg/` (ويب).
مكتبة **itshover** كاملة (٢٦٣ أيقونة، Apache-2.0) متاخدة من مستودعهم ومولّد منها نسخة للمحركين — الشرح في `docs/icons.md`.

---

## حالة البيئة (اللي اتظبط)

| القدرة | الحالة |
|---|---|
| Python: Pillow · numpy · scipy · OpenCV · PyAV · HarfBuzz · FreeType | ✅ |
| FFmpeg 7.0.2 (x264/aac) + بديل `ffprobe` متوافق | ✅ |
| Arabic shaping: بديل HarfBuzz+FreeType (`arabic_shape.py`) لأن Pillow هنا من غير libraqm | ✅ |
| Chromium (من `@sparticuz/chromium`) لمحرك K | ✅ |
| خط Cairo (OFL) في `assets/fonts/Cairo` | ✅ |
| محركي الرندر P و K | ✅ اتجربوا ورندروا فريمات عربية صح |
| الاختبارات (`make test` · `make selftest`) | ✅ ٧٦ اختبار + رندر من المحركين |
| مفتاح ElevenLabs | ❌ اختياري — الصوت بييجي منك |

شغّل `python3 tools/doctor.py` في أي وقت للتأكد.

---

## الترخيص

الحزمة في `medo-motion/` هي نسخة خاصة من **«موشن خام» — Khaam Motion v1.4.1**
لـ خام (@khaam.hq) / راشد الحازمي، معدّلة لميدو. رخصتها تسمح باستخدامها في فيديوهاتك
الخاصة والتجارية وللعملاء، و**تمنع** إعادة نشر المهارة نفسها أو بيعها أو نشر نسخة معدّلة
منها كمنتج. التفاصيل في `medo-motion/LICENSE.md`. الخطوط والمؤثرات بتراخيصها (OFL / CC0).
