# تثبيت وتشغيل مشروع Video Motion

**Video Motion مستودع مشروع كامل، وليس ملف Skill مستقلًا للتوزيع.** ابدأ دائمًا من
جذر المستودع حتى تكون المسارات والقوالب والاختبارات متاحة معًا.

## المتطلبات

- Python لتشغيل أدوات الفحص والبناء والمحرك P.
- Node.js وnpm للمحركين K وR والأدوات المشتركة.
- FFmpeg وffprobe لإخراج الفيديو والتحقق منه.
- Chromium وPlaywright للمحرك K، ويعاد استخدام إعداد المتصفح الذي يجهزه المشروع.
- بعض الحزم الصوتية اختيارية ولا يلزم تثبيتها إلا عند استخدام وظائفها.

## إعداد البيئة

من جذر المستودع:

```bash
bash tools/setup.sh
python3 tools/doctor.py
python3 tools/selftest.py
```

اختبارات المحركات الموسعة:

```bash
python3 tools/selftest.py --remotion --hybrid
```

هذه الأوامر تفحص البيئة وتنفذ اختبارات فعلية؛ راجع أثر أي أمر قبل تشغيله على مشروع يحتوي بيانات مهمة.

## الأدوات الاختيارية المجانية

FFmpeg يأتي مع `bash tools/setup.sh` (نسخة ثابتة من `imageio-ffmpeg` داخل `tools/bin/`). الأدوات
الثلاث التالية اختيارية ولا يحتاجها أي من المحركات P/K/R؛ ثبّت ما ستستخدمه فقط:

```bash
bash tools/setup_extras.sh whisper       # faster-whisper + نموذج Whisper-small محلي (~480 MB)
bash tools/setup_extras.sh demucs        # Demucs لفصل المسارات (يسحب PyTorch — عدة جيجابايت)
bash tools/setup_extras.sh hyperframes   # HyperFrames CLI 0.9.9 معزول (يتطلب Node >= 22)
bash tools/setup_extras.sh all
bash tools/setup_extras.sh --check       # جرد فقط بلا تثبيت
```

| الأداة | الرخصة | الاعتماديات | الاستخدام |
|---|---|---|---|
| FFmpeg | بحسب البناء (GPL للنسخة الثابتة) | `tools/requirements.txt` | كل المحركات |
| Whisper | MIT | `tools/requirements-align.txt` | `tools/whisper_align.py`، `tools/caption_align.py` — `docs/alignment.md` |
| Demucs | MIT | `tools/requirements-stems.txt` | `tools/stems.py`، `medo-motion/scripts/analyze_ref.py --stems` — استماع ومحاذاة فقط |
| HyperFrames | Apache-2.0 | `tools/optional-hyperframes/` | `tools/html_scene.py` (و`bash tools/hyperframes.sh …` للـCLI الخام) — مسار تجريبي، ليس محركًا رابعًا (`docs/hyperframes-fit.md`) |

- أوزان Demucs (`htdemucs`) تُنزَّل عند أول تشغيل من `dl.fbaipublicfiles.com`؛ في بيئة مقيدة الشبكة يفشل هذا التنزيل.
- `tools/html_scene.py new` يولّد مشهدًا أوفلاين بلا GSAP ولا CDN (خطوط من `assets/fonts/` وألوان `brand.json`). قوالب HyperFrames الأصلية (`init`) تستدعي GSAP من CDN وتفشل بلا شبكة.
- النماذج والأوزان و`node_modules` لا تدخل Git.

## استخدام المشروع مع وكيل برمجي

1. افتح جذر المستودع في وكيل لديه صلاحية الوصول إلى الملفات وتشغيل الأوامر.
2. اطلب منه قراءة `AGENTS.md` أولًا، ثم `medo-motion/SKILL.md` عند الحاجة.
3. استخدم `medo-motion/START-HERE.md` كمسار إرشادي سريع.
4. أنشئ مشروع فيديو جديدًا باستخدام `tools/new_project.py` واختر المحرك المناسب.
5. اتبع خطوات التحقق والرندر ومعايير التسليم في `AGENTS.md`.

## اختلاف بيئات التشغيل

- وكيل يعمل على جهازك ويملك وصولًا للملفات يستطيع تنفيذ دورة الرندر المحلية.
- واجهة محادثة لا تملك وصولًا مباشرًا لجهازك يمكنها المساعدة في التخطيط والسكريبت والمراجعة، لكنها لا تستطيع الادعاء بأنها رندرت ملفات على جهازك.
- لا تفترض وجود متصفح أو مكتبات أو مفاتيح API لمجرد أن ملفاتها مذكورة في التوثيق.

## الخدمات الاختيارية والاعتمادات

خدمات TTS أو توليد الصوت الخارجية اختيارية. لا يلزم وجود حساب ElevenLabs لتشغيل محركات الفيديو الأساسية. لا تُرسل طلبًا مدفوعًا ولا تثبّت اعتماديات إضافية دون موافقة واضحة.

## التحقق بعد الإعداد

- `python3 tools/doctor.py`: حالة البيئة والأدوات.
- `python3 tools/selftest.py`: الاختبارات العامة ورندر P/K الأساسي.
- `python3 tools/selftest.py --remotion --hybrid`: اختبار R وتجميع Hybrid فعليًا.
- `bash tools/ci.sh`: بوابات الجودة الثابتة المستخدمة في CI.

راجع تقارير GitHub Actions عند تشغيل CI، ولا تخلط بين نجاح فحوصات الكود وبين نجاح رندر فعلي لكل محرك.
