# Medo Motion — موشن ميدو (v1.0)
نسخة خاصة من «موشن خام» v1.4.1 + هوية Kodo Medo + محرك الريلز الإجرائي. **للاستخدام الشخصي فقط، ممنوع إعادة النشر** (انظر `LICENSE.md`).

| فين | إيه |
|---|---|
| `brand/BRAND.md`, `brand/brand.json` | الهوية المقفولة (ألوان، خطوط، مناطق آمنة، صوت، تصدير) |
| `reference/medo-playbook.md` | قرارات الدمج + عقد ميدو + خطوات المحركين + الأخطاء + التسليم |
| `reference/source/AGENT_MASTER_BRIEF_v4.md` | الملف الأصلي كامل (للمرجعية) |
| `templates/procedural-reels/` | محرك P: Pillow+OpenCV+FFmpeg، chunks قابلة للاستئناف، mix بـ loudnorm |
| `templates/render/` | محرك K: Canvas/Playwright (+ `lib/brand.js`) |
| `styles/medo-red-circle.md` | الستايل الأساسي |
| `scripts/brand_check.py` | فحص التباين والانحراف عن البالِت |

---
# (الأصل) Khaam Motion
# «موشن خام» — Khaam Motion v1.4

مهارة لـ Claude تخليه **مخرج موشن جرافيك** كامل: يكتب الفكرة، ويصمم، ويحرّك، ويضيف الصوت، ويطلّع لك فيديو MP4 جاهز. **عربي أولاً.**

من «خام» (@khaam.hq) — إعداد **راشد الحازمي**.

## أول مرة؟
افتح **`START-HERE.md`** (ابدأ هنا)، أو أعطِ المجلد كامل لـ Claude وقل له: **«ابدأ»**. هو يوجهك خطوة بخطوة.

## وش تقدر تسوي فيها
- **مرة وحدة وكاملة:** توافق على الخطة، وأول فيديو يوصلك فيه الحركة والمؤثرات والصوت مع بعض. ويتذكر ستايلك وتفضيلاتك في كل فيديو جديد.
- **الهوك أولاً:** أول ٣ ثواني تنبني على هوك مدروس (يبحث عن هوكات مجالك ويقترح ٣)، والحركة تخدمه.
- فيديوهات موشن من الصفر: نصوص متحركة، وأشكال، و3D، وبطاقات، ومخططات.
- **نصوص عربية صح:** الحروف ما تتكسر، والاتجاه من اليمين، وخطوط عربية مجربة (`reference/arabic-typography.md`).
- **فهرس خطوط عربية** فيه وصف كل خط ومتى تستعمله ورخصته، والمجانية تنزل بأمر واحد (`reference/arabic-fonts.md`).
- **ستايلك أنت:** أعطه مراجعك أو هويتك، ويبني لك ستايل ويحفظه. وفيه 8 أمثلة للإلهام لو تبي نقطة بداية (`styles/`).
- **نظام ريلز الشرح:** هيكل السكربت، والإطار الثابت، والكابشن، والانتقالات، وخاتمة «علّق الكلمة»، مع عناصر جاهزة (جوال، ونافذة برنامج، وقائمة مهام، وختم، وعدّادات) في `reference/explainer-reel-system.md`.
- **مؤثرات صوتية مجانية** من Openverse، برخص واضحة (`reference/free-sfx-openverse.md`).
- **صوت معلّق بالذكاء الاصطناعي** من ElevenLabs بنموذج Eleven v4، متزامن مع الحركة والكابشن. Claude يعرضه عليك أول مرة ويشرح كيف تربط مفتاحك (اختياري، بحسابك).
- تعديل فيديوهاتك المصوّرة: قص، وكابشن، وإضافات.

## وش تحتاج
| الشي | ضروري؟ | ملاحظة |
|---|---|---|
| اشتراك Claude مدفوع (Pro أو أعلى) | ✅ | عشان **Claude Code**، وهو اللي يرندر الفيديو على جهازك |
| Python 3.10+ وNode 18+ وFFmpeg | ✅ | Claude يتأكد منها ويثبّت الناقص بعد ما تأذن له |
| Playwright + Chromium | ✅ | للرندر. Claude يثبّته بإذنك |
| مفتاح ElevenLabs | اختياري | للصوت المعلّق والمؤثرات المولّدة |

**أفضل نتيجة:** Opus 5.5 مع أعلى effort (**max**).

## الملفات
| الملف | وش فيه |
|---|---|
| `START-HERE.md` | ابدأ هنا: التثبيت والتشغيل الأول |
| `SKILL.md` | تعليمات Claude الرئيسية |
| `reference/` | الأدلة: العربي، والخطوط، والتصميم، والصوت، والتسليم |
| `styles/` | بناء ستايلك، وأمثلة للإلهام |
| `scripts/` | أدوات: الفحص، وتنزيل الخطوط، والأصوات، والمعاينة |
| `templates/` | قالب الرندر، وملف الذوق `TASTE.md`، ولوحة التصميم |
| `CHANGELOG.md` | الإصدارات |
| `LICENSE.md` | الرخصة: مجانية للاستعمال، وممنوع إعادة النشر |

---
## English
**Khaam Motion v1.4** by Khaam (@khaam.hq), edited by Rashed Alhazmi. A Claude skill that directs, designs, animates and sound-designs motion graphics and renders MP4 locally. Hook-first (researched 3-second hooks drive the motion). Arabic-first: correct RTL typography, an Arabic font catalog with an OFL downloader, the user's own style first with 8 example looks, an explainer-reel directing system with a component kit, free Openverse sound effects, optional ElevenLabs narration. Start with `START-HERE.md`. Requires a paid Claude plan for Claude Code; best with Opus 5.5 at max effort.
