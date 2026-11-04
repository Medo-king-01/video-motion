# مراجعة OpenMontage — إيه اللي كان عندنا، وإيه اللي بنيناه نظيفًا، وإيه اللي رفضناه

> فحص معماري نظيف (Clean-Room) لمستودع [`calesthio/openmontage`](https://github.com/calesthio/openmontage)
> عند الـcommit `d21f5d4eaa08422b09c7091757a05affcbabb35b` (`main`, 2026-11-03).
> **رخصة OpenMontage هي `AGPL-3.0`**؛ لذلك لم نقرأ أو ننسخ أو نستورد أي ملف كود مصدري (`.py`/`.ts`) منه،
> واقتصر الفحص على التوثيق العام (`README.md` و`docs/ARCHITECTURE.md`) لبناء مكافئات أصلية ١٠٠٪ داخل عقود استوديو ميدو.

---

## ١. إيه هو OpenMontage في سطرين؟

منصّة إنتاج فيديو «الوكيل فيها هو المنسّق» (`Agent-as-Orchestrator`) تقسّم العمل إلى ٨ مراحل
(`research → proposal → script → scene_plan → assets → edit → compose → publish`) عبر ١٣ مسار إنتاج،
٥٧+ أداة موحّدة تحت سجل قدرات (`support_envelope`)، ٣ محركات تركيب (`Remotion` و`HyperFrames` و`FFmpeg`)،
خادم مراجعة محلي (`Backlot`)، وبوابة مراجعة ذاتية قبل التسليم (`Self-Review` + `Delivery Promise Verification`).

استوديو `video-motion` مختلف جوهريًا في الغرض: **هو استوديو ريلز مصري مقفول الهوية، أوفلاين وقت الرندر،
ومبني حول محركاتنا التلاتة (`P` و`K` و`R` + `Hybrid`) بصوت ميدو وشخصيته وبالِتته الـ١٢ لون**.

---

## ٢. اللي كان موجود عندنا بالفعل (وأعمق في مجاله)

قبل أي إضافة، معظم البنية الجوهرية في OpenMontage ليها مقابل أصيل ومُختبر عندنا:

| المفهوم في OpenMontage | المقابل الأصيل في `video-motion` |
|---|---|
| تعدد محركات التركيب (`Remotion` / `HyperFrames` / `FFmpeg`) | `P` (Pillow/OpenCV) + `K` (Canvas/Playwright) + `R` (Remotion) + `tools/render_hybrid.py` للمقاطع المتتابعة |
| ملفات الماركة والستايل (`styles/*.yaml`) | `medo-motion/brand/brand.json` المقفول + `TASTE.md` + `STYLE.md` + `medo-motion/styles/` + `brand_check.py` |
| تخطيط المشاهد على الإيقاع والكلمات | `tools/vo_length.py` + `align_captions.py` + `text_direction.py` + `visual_direction.py` + `techniques.py --draw` |
| قواعد الحرفة قبل الرندر | `tools/reel_lint.py` (`S01`–`S12`، `A01`–`A03`، `T00`–`T06`، `V01`–`V04`) |
| فحص تصادم النصوص والوجوه | `tools/layout_audit.mjs` لمحرك `K` (`L00`–`L03` + `--replay` `R01`/`R02`) |
| هندسة الصوت والـDucking والـLoudness | `mix.py` و`safe_audio.py` (two-pass EBU R128 `-14.5 LUFS` + `-1.5 dBTP` + sidechain ducking) |
| تفكيك فيديو مرجعي | `medo-motion/scripts/analyze_ref.py` + `docs/reference-workflow.md` |

---

## ٣. الفجوات الأربع الحقيقية اللي بنيناها جوه مشروعنا

رغم قوة فحوص **ما قبل الرندر** عندنا (`reel_lint.py` و`brand_check.py`)، الفحص كشف ٤ فجوات حقيقية
في مرحلة **ما بعد الرندر** وفي تكافؤ محرك `P` مع `K`:

### أ) بوابة فحص الفيديو النهائي بعد الرندر — `tools/media_qa.py` (`make qa`)

كانت مواصفات القبول في `AGENTS.md §7` (`1080×1920 @ 30fps`، `H.264 High + yuv420p + faststart`،
`≥ 2.5 Mbps`، عدم وجود كادرات سوداء أو ثبات > ٢.٥ ثانية، و`-14.5 ± 0.3 LUFS` / `≤ -1.5 dBTP`)
مكتوبة كقائمة مراجعة يدوية من غير أداة واحدة تفحص الـMP4 النهائي وتمنع التسليم لو بايظ.

بنينا `tools/media_qa.py` يفحص الـMP4 الفعلي بـPyAV وFFmpeg `ebur128` وفحص ذرّات الحاوية:

| الكود | اللي بيتقاس فعليًا على ملف الـMP4 |
|---|---|
| `Q00` | حاوية صالحة، مسار فيديو `h264` (`High` في الماستر) بـ`yuv420p`، وترتيب ذرّات `moov` قبل `mdat` (`+faststart`) |
| `Q01` | أبعاد `1080×1920`، `30fps` ثابتة، ومطابقة المدة وعدد الإطارات مع `--vo` و`--beats` و`--expected-frames` |
| `Q02` | معدل البت في الماستر `≥ 2.5 Mbps` (قابل للتخصيص بـ`--min-mbps` مع تسجيل العتبة في التقرير) |
| `Q03` | فريم `0` مش أسود ولا خلفية سادة ناعمة، ومفيش سقوط لكادرات سوداء وسط الفيديو |
| `Q04` | مفيش ثبات بصري متصنّم (`diff_p99 < 1.5`) أطول من `2.5s` متصلة |
| `Q05` | مسار صوت `AAC` موجود في الماستر، وقياس EBU R128 الفعلي داخل `-14.5 ± 0.3 LUFS` و`TP ≤ -1.5 dBTP`، وبلا clipping أو صمت ميت (مع حالة `incomplete` الصريحة للمقاطع الأقصر من ثانية بدل ادعاء قياس كاذب) |

وكمان وصّلناها اختياريًا بـ`tools/render_hybrid.py --qa [--qa-mode ...] [--qa-report ...]` بحيث يفحص الملف المؤقت **قبل** نشره لـ`out/hybrid.mp4`، فلو فشل الفحص لا يُنشر ملف معطوب أصلًا.

```bash
python3 tools/media_qa.py projects/my-reel/out/master.mp4 \
  --mode master \
  --vo projects/my-reel/out/vo24.wav \
  --beats projects/my-reel/plan/beats.json \
  --sheet projects/my-reel/cache/final-qa-sheet.png \
  --json projects/my-reel/cache/final-qa.json
```

### ب) فحص التخطيط والثبات لمحرك P — `layout_p.py` + `tools/layout_audit_p.py` (`make layout-p`)

محرك `K` كان عنده `tools/layout_audit.mjs`، بينما محرك `P` (المحرك الأساسي لريلز ميدو الحوارية!)
مكنش عنده فحص آلي لتصادم النصوص أو تغطية الوجوه أو ثبات الإطارات عند الـseek العكسي.

أضفنا `medo-motion/templates/procedural-reels/layout_p.py` مع ربط اختياري غير كاسر في
`captions.py` و`presenter.py` (`face_box` / `face_boxes` شاملة `PoseTrack`) و`scenes.py` (`camera()`),
وأداة `tools/layout_audit_p.py` بنفس عقود وأكواد `layout_audit.mjs`:

- `L00`: مستطيل غير صالح أو منطقة غير معروفة أو غياب `face_box` مقاس لوضعية مرسومة.
- `L01`: خروج النص عن منطقته الآمنة في `brand.json` (`content`: `200..1350`، `caption`: `1350..1500`، `hud`: `0..200`، هامش `40px`).
- `L02`: تصادم مستطيلات النصوص أو تغطية منطقة محمية (`≥ 2px` على المحورين).
- `L03`: نص يغطي مستطيل وجه المذيع حتى لو بـ`1px`، مع أخذ زوم وإزاحة الكاميرا في الحسبان لو النص خارج الـHUD.
- `--replay` (`R01` / `R02`): يرندر الإطارات بترتيب عكسي ويقارن الـRGB والـboxes فريم بفريم لكشف أي state ملوّث بين الـchunks.
- صور معلَّمة بحدود `#CB271B` للكادرات المخالفة + `report.json` متطابق في البنية مع محرك `K`.

```bash
python3 tools/layout_audit_p.py --project projects/my-reel \
  --out projects/my-reel/cache/layout-p --replay
```

### ج) بوابات المراحل ووعد التسليم — `tools/stage_gate.py` (`make gate`)

استلهمنا من OpenMontage فكرة التحقق المتراكم عبر المراحل وفحص «وعد التسليم» (`Delivery Promise Verification`)،
لكن نفّذناها بدون خادم خلفي ولا أرشيف مشاريع داخل Git:

- `G01` (`intake`): اكتمال `BRIEF.md` و`plan/script.md` ووجود تسجيل التعليق الصوتي (ورفض نصوص الـscaffold الفاضية).
- `G02` (`plan`): التحقق من أن `out/vo24.wav` هو WAV أحادي `24 kHz PCM16` ومطابقته لـ`plan/beats.json` وكود المشاهد عبر `vo_length.py --check`.
- `G03` (`plan`): اكتمال `copy.json` و`text-direction.json` و`visual-direction.json` (إن وُجد) و`techniques.json`.
- `G04` (`plan`): نجاح `reel_lint.py --scan-code` و`brand_check.py --project`.
- `G05` (`render`): وجود الـMP4 المخرج ونجاح تقرير فحص الكادر (`--layout-report` لـ`K` أو `P`).
- `G06` (`deliver`): نجاح `media_qa.py --mode master` على الـMP4 النهائي، والتأكد من توثيق أي أصل خارجي في `CREDITS.md`، ومنع أي `CHIP`/اسم سلسلة غير معتمد من المستخدم (`approvedByUser: true`).
- `--write-checkpoint` و`--verify-checkpoint`: يحفظ بصمة `SHA-256` لكل ملفات الخطة والـVO والـMP4 داخل `<project>/cache/stage-gate.json` (المتجاهل في Git)؛ لو اتعدّل أي ملف بعد الاعتماد ترفض البوابة بـ`STALE_CHECKPOINT`.

```bash
python3 tools/stage_gate.py projects/my-reel --stage plan --write-checkpoint
python3 tools/stage_gate.py projects/my-reel --stage deliver \
  --media out/final.mp4 \
  --layout-report cache/layout-p/report.json
```

### د) مظروف القدرات الآلي للوكيل — `tools/doctor.py --json`

في OpenMontage يعيد سجل الأدوات `support_envelope` منظّمًا يقرأه الوكيل قبل اختيار خطة التنفيذ بدل قراءة سطور نصية.
أضفنا `python3 tools/doctor.py --json` ليُخرج JSON حتمي يتضمن الحالة الكلية (`READY` / `DEGRADED` / `BLOCKED`)،
واجهة تشكيل العربي النشطة، وحالة كل محرك على حدة (`P`، `K`، `R`، `Hybrid`) مع الحفاظ الكامل على المخرجات النصية القديمة.

---

## ٤. اللي رفضناه عمدًا وسببه

| عنصر في OpenMontage | قرارنا | السبب |
|---|---|---|
| استيراد أو نسخ كود من المستودع | **مرفوض** | رخصة `AGPL-3.0` تتعارض مع نظافة تراخيص الاستوديو |
| موفرو الـAI السحابيين (57+ أداة توليد فيديو/صوت/بحث) | **مرفوض** | استوديو ميدو أوفلاين وقت الرندر وممنوع استدعاء شبكات أو مفاتيح مدفوعة خفية |
| تعدد المقاسات والستايلات العامة (`16:9`، `1:1`، YouTube، إلخ) | **مرفوض** | عقدنا مقفول على `1080×1920 @ 30fps` وبالِتة الـ١٢ لون في `brand.json` |
| خادم `Backlot` الدائم وأرشفة المشاريع | **مرفوض** | `projects/<slug>/` مساحة عمل مؤقتة (`test_studio_not_archive.py`) وعندنا `tools/motion_studio.html` الأوفلاين |
| استبدال محرك `K` بـ`HyperFrames` | **مرفوض سابقًا** | سبق قياسه وحسمه في `docs/hyperframes-fit.md` |

---

## ٥. حدود صريحة لا ندّعيها

- `media_qa.py` يفحص جودة الحاوية، التزامن، السطوع، الحركة، والـLUFS، لكنه **لا يقرأ جمال التكوين أو صحة إملاء العربي بصريًا** — مراجعة الـcontact sheet بالعين واجبة كما ينص `AGENTS.md §7`.
- فحص الفريم الأول في `media_qa.py` يلتقط الفريم الأسود والخلفيات الناعمة الفاضية، لكن الخلفيات الرسومية عالية التباين (`glyphs` و`pulse` و`perspective`) تحتوي خطوطًا مقصودة؛ لذلك يظل فحص وجود عنصر أمامي دلاليًا مسؤولية `reel_lint.py` (`S06`) قبل الرندر.
- قياس الـIntegrated LUFS في EBU R128 يحتاج نافذة بوابات `≥ 1.0s`؛ المقاطع الأقصر من ثانية تُوسم `incomplete` في وضع `master` بدل تمريرها أو تخطئتها عشوائيًا.
