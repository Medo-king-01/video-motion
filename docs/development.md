# إعداد البيئة والتطوير من clone لحد مشروع قابل للحفظ

كل الأوامر من **جذر المستودع الكامل**. `medo-motion/` مش حزمة مستقلة.

## المتطلبات والخطوات

- [Python](https://www.python.org/downloads/): يفضل **3.12**. توافق الكود بيتفحص على 3.10 و3.12.
- [Node.js](https://nodejs.org/en/download): **20.11+** مع npm؛ يفضل إصدار LTS مدعوم.
- Linux/macOS أو WSL على Windows؛ `venv` وpip لازم يكونوا متاحين (بعض توزيعات Linux محتاجة حزمة `python3-venv`).
- مفيش `sudo` أو تثبيت Python/Node أو تغيير system Python جوه السكربت.

```bash
git clone https://github.com/Medo-king-01/video-motion.git
cd video-motion
python3 -m venv .venv
source .venv/bin/activate
bash tools/setup.sh --dev
bash tools/setup.sh --dev --check
make ci
python3 tools/selftest.py --remotion --hybrid
```

`setup` بيثبت حزم Python من baseline محدد، وNode toolkit بـ`npm ci`، وبينزّل/يربط FFmpeg من
imageio-ffmpeg لو مش موجود، وبيجهز ffprobe shim لو مفيش ffprobe أصلي، وبيتحقق من الخطوط
وبيكمل الناقص، وبعدها بيشغّل doctor (بيفتح Chromium فعليًا). أي فشل بيرجع exit code غير صفري.
ملفات التنفيذ المحلية في `tools/bin/`؛ ضيفه لـPATH في جلساتك الجديدة لو محتاج:

```bash
export PATH="$PWD/tools/bin:$PATH"
```

- من غير `--dev`: حزم التشغيل بس؛ `make test` و`make ci` محتاجين `--dev`.
- `--check`: inventory للمتطلبات والإصدارات وملفات الخطوط وحزم Node، **من غير كتابة أو تثبيت أو فتح browser**.
  مش بديل لاختبار doctor الوظيفي؛ وجود binary مش ضمان إنه شغال.
- ممكن تختار Python محدد: `PY=/path/to/venv/bin/python bash tools/setup.sh --dev`.
- مفيش مفاتيح API مطلوبة للإعداد أو CI أو selftest. عبّي أي مفتاح اختياري محليًا، مش في الشات.

## مثال مشروع مصغر مطابق للسكافولد

```bash
python3 tools/new_project.py my-reel --engine p
```

```text
projects/my-reel/
  BRIEF.md                  # السكريبت، اتجاه المشاهد، الصوت، الصور
  PROGRESS.md
  TASTE.md
  STYLE.md
  plan/beats.json           # draft: duration=null، scenes=[]؛ لازم قياسات VO قبل الرندر
  plan/script.md
  plan/text-direction.json  # اختيار الخط وحركة كل نص، مفيش default
  plan/copy.json
  assets/vo/                # حط تسجيلك هنا
  assets/poses/poses.json   # مكتبة مشتركة اتنسخت؛ سجل أي وضعية جديدة هنا
  assets/fonts/fonts.json
  assets/refs/
  scenes.py                 # وباقي ملفات محرك P
  out/                      # متجاهل
  cache/                    # متجاهل
```

املأ المدخلات الأربعة في `projects/my-reel/BRIEF.md` واتبع `AGENTS.md`.
السكافولد مسودة مش فيديو مكتمل ومش بيفترض توقيت صوت مش موجود.
**مجلد المشروع مش بيتتبع في Git:** `projects/*` مستثنى بالكامل، وكل سكافولد بيكتب ملف
`.gitignore` فيه `*`. راجع الأصول وحقوقها في `assets/CREDITS.md`، وسلّم الفيديو، وبعدها امسح
المجلد أو انقله بره المستودع (`--out ~/reels/my-reel` لو تحب تحتفظ بيه من الأول).
`--force` بيعيد كتابة ملفات السكافولد الموجودة؛ مش وسيلة دمج أو backup. بيترفض لو الهدف أو أي ملف تحته symlink.

## سياسة الاعتماديات

- `tools/requirements.txt`: runtime؛ `requirements-dev.txt`: runtime + pytest/Ruff.
- الاتنين بيستخدموا `tools/constraints.txt`: إصدارات مراجعة للتبعيات الأساسية والمتعدية المعروفة، مش lock شامل
  لكل نظام/معمارية أو لحزم ASR الاختيارية. حدّث القيود عمدًا وجرب مصفوفة CI والـselftest؛ متشيلهاش عشان تعدّي install.
- Python 3.10 بيستخدم Pillow 12.3؛ Python 3.11+ بيستخدم Pillow 13.0. **تنبيه أمني:** إصلاحات Pillow الأحدث
  مش متاحة كلها لـ3.10. استخدم 3.12 لمعالجة ملفات غير موثوقة؛ اختبار التوافق مش ضمان غياب الثغرات.
- toolkit وقالب Remotion معاهم lockfiles؛ استخدم `npm ci`. لو غيرت package.json، حدّث lockfile عمدًا واختبره.
- `tools/font-packages.lock.json`: إصدار وSHA-512 لكل حزمة خطوط npm؛ installer بيتحقق من الأرشيف قبل الاستخراج.
  الكاش مربوط بالإصدار؛ الأصول المضمّنة الحالية مش بيتغير محتواها تلقائيًا. `--force` بيعيد التثبيت من المصدر المقفول.
  `FAMILIES` في `tools/fonts_install.py` هو مصدر قائمة العائلات والأوزان؛ doctor وsetup و`--check`
  بيفحصوا manifest وملفات كل عائلة وOFL الفعلية، مش عدد المجلدات بس.
- GitHub Actions بيشغّل quality gates على Python 3.10/3.12، والرندر الكامل على 3.12.
  نتيجة GitHub نفسها مش بتُعتبر ناجحة إلا بعد تشغيل workflow؛ الاختبار المحلي بيستخدم إصدار الجهاز.

## حدود الأمان والأصول

- `.env` بيتكتب atomically بصلاحيات POSIX `0600`، من غير طباعة قيم؛ الروابط الرمزية للهدف ومكونات مساره مرفوضة.
  Windows محتاج ACL مناسب للمستخدم؛ POSIX mode مش ضمان ACL هناك.
- الأدوات اللي اتقوّت بترفض symlinks قبل الكتابة/التنظيف؛ **مش sandbox ضد مستخدم عدائي بيغيّر الملفات بالتزامن**.
  شغّلها في workspace محلي تملكه، مش مجلد قابل للكتابة من مستخدمين غير موثوقين.
- تنزيل الخطوط العام `get_fonts.py` بيستخدم مجلد باسم آمن normalized، مش اسم المستخدم كمسار.
- سكربت الرندر المقسم بيستخدم tempfile فريد؛ مش بيمسح `.part.mp4` قديم.
- فحوص التبعيات الأمنية في `dependency-audit.yml` دورية/يدوية، بتبلغ بالفشل من غير auto-fix.
  راجع كمان Secret scanning / push protection في إعدادات GitHub لو متاحة لحسابك/خصوصية المستودع؛ دي إعدادات خدمة،
  مش حاجة بنفعلها من الكود، ومافيش هنا ادعاء إن كل الأسرار أو الثغرات اتفحصت.
- الخطوط والصور الحالية متسابين زي ما هم للحفاظ على الجودة وتراخيصها. ضغطها أو تحميلها عند الطلب قرار منفصل
  محتاج قياس جودة وحجم وموافقة المالك. [حالة الترخيص](../medo-motion/LICENSE.md) ما اتغيرتش؛
  تراخيص الأطراف الخارجية في [Credits](../assets/CREDITS.md) مش ترخيص للكود الأصلي.
