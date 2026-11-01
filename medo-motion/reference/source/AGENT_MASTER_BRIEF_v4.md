# PROCEDURAL REELS — AGENT MASTER BRIEF (v4)
> ملف تنفيذ واحد مكتفي بنفسه. اتبنى من مشروع حقيقي اتسلّم (فيديو "مقدمة سلسلة اختيار اللابتوب": 55.2 ثانية، 1080×1920، صوت -14.5 LUFS).
> **الكود الكامل اللي اشتغل موجود في الملحق (Appendix) في آخر الملف. ابدأ منه، متكتبش من الصفر.**
> اللغة مع المستخدم: **عامية مصرية، قصيرة ومحددة.** الكود والتعليقات الداخلية إنجليزي.
>
> **الجديد في v4:** العناصر مابقتش "كود بس". بقى مسموح (ومطلوب) **توليد الصور بالـ AI** و**البحث في الإنترنت** لجلب أصول — بشرط ستايل واحد مقفول، وبوابات جودة، وتوثيق للترخيص. كل التفاصيل في **القسم 11**. باقي الملف زي ما هو، والملحق (الكود) ما اتغيرش.

---------------------------------------------------------------------
## 0. العقد (اقرأه قبل أي حاجة)
1. المطلوب **ملف MP4 جاهز للنشر**، مش ستوري بورد ولا خطة.
2. العناصر على الشاشة **مش كود بس** — فيه سلّم مصادر محدد (القسم 11): **(أ) كود** = الافتراضي للنصوص والكروت والجداول والأشرطة والأشكال التجريدية؛ **(ب) توليد AI** = للأبطال اللي الكود بيطلعهم باهتين (أجهزة، منتجات، شخصيات، مشاهد)؛ **(ج) بحث في الإنترنت** = لما تحتاج أصل حقيقي مرخّص. الشرط الحاكم مش "مين رسمها" — الشرط إن **الستايل واحد مقفول** و**كل أصل مفحوص على خلفية متباينة** قبل ما يدخل الكادر.
3. **اسأل مرة واحدة فقط** (القسم 1) ثم اشتغل. لو حاجة ناقصة: قرّر، واكتب قرارك في سطر.
4. **ابعت سطر حالة كل ~2 دقيقة** أثناء الشغل الطويل ("شغال على كذا"). الصمت الطويل بيتفهم إنه فشل.
5. **اعرض بصريًا قبل ما تسلّم**: contact sheets من الفريمات، 3 جولات مراجعة على الأقل.
6. **اصدق في الحاجات اللي مش متأكد منها** (حدود المشاهد، الخط المؤقت، مكان اللوجو) واكتبها في رسالة التسليم.

## 1. اللي تطلبه من المستخدم (رسالة واحدة)
| # | المطلوب | لو ناقص |
|---|---|---|
| 1 | السكريبت: beats مرقمة، كل beat فيها جملة الـ VO + اللي يظهر على الشاشة | إلزامي |
| 2 | ملف الصوت (واحد أو لكل beat) | إلزامي (أو يقول اعمل TTS) |
| 3 | صور المقدم 2–4 وضعيات (خلفية بيضا أو خضرا) | ارسمه بالكود، ولو طلع باهت → **ولّده بالـ AI** بنفس ستايل المشروع واقطعه (11-ب) |
| 4 | اسم السلسلة + اللوجو + رقم الحلقة | chip وصفي مؤقت + دايرة فاضية للوجو |
| 5 | ملف الخط العربي (Cairo-Bold / Tajawal-ExtraBold) | استخدم DejaVu Sans Bold **واكتب إنه مؤقت** |
| 6 | الألوان | الأحمر/الأسود/الأبيض + أصفر/زمردي/تيل كلمسات |
| 7 | موسيقى جاهزة | اصنع bed بالكود (موجود في mix.py) |
| 8 | أصول إضافية (أجهزة/منتجات/أيقونات كبيرة) | **ولّدها أو ابحث عنها** بنفسك (القسم 11) — واعرضها على المستخدم قبل ما تعتمدها |

## 2. الفحص الأول للبيئة (دقيقة واحدة — بيحدد كل القرارات)
```bash
which ffmpeg ffprobe python3; nproc; free -g
python3 -c "from PIL import features; print('raqm', features.check('raqm'))"   # لازم True وإلا العربي يتكسر
python3 -c "import cv2, scipy, numpy, PIL; print('libs ok')"
python3 -c "import whisper" ; python3 -c "import faster_whisper"               # غالبًا مش موجودين
fc-list :lang=ar family | sort -u                                              # فيه Cairo؟
ffprobe -hide_banner voice.wav                                                 # المدة الحقيقية
```
- `raqm=False` → وقف وقول للمستخدم. **ممنوع `arabic_reshaper`/`python-bidi` مع Pillow.** الصح: `ImageDraw.text(..., direction='rtl', language='ar')`.
- البيئة اللي اتجربت: CPU واحد، ~3GB RAM، من غير نت. الريندر ≈ 0.11–0.15 ث/فريم → 1656 فريم ≈ 6 دقايق.
- لو ملف الـ wav الهيدر بتاعه "غلط" لـ scipy (حصل): حوّله الأول `ffmpeg -i in.wav -ac 1 -ar 24000 -c:a pcm_s16le out/vo24.wav`.
```bash
python3 -c "import rembg; print('rembg ok')"   # لو ناقص: pip install "rembg[cpu]"  (موديل u2net ~176MB)
curl -sI https://fonts.google.com | head -1    # فيه نت؟ (توليد/بحث)
nvidia-smi 2>/dev/null || free -m              # الميموري بتحكم حجم التوليد/التقطيع
```
- **مفيش نت؟** اقفل على الكود، وقول للمستخدم في سطر واحد إن التوليد/البحث مش متاح في البيئة دي.

## 3. خطوات الشغل (بالترتيب — كل خطوة ليها نقطة تحقق)

**S1. تقسيم الصوت على المشاهد من غير تفريغ نصي**
```bash
ffmpeg -hide_banner -i voice.wav -af silencedetect=noise=-35dB:d=0.35 -f null - 2>&1 | grep silence_
```
1. وزّع جمل السكريبت على الفواصل بين السكتات. **تحقق بمعدل الكلام: عدد الحروف ÷ مدة المقطع ≈ 11–16 حرف/ث.** لو طلع 8 أو 22 → التوزيع غلط، اضبطه.
2. حدود المشاهد = **منتصف السكتة** بين آخر جملة وأول جملة في المشهد التالي. (الـ wipe بيتحط هناك.)
3. جوه الجملة الطويلة: وزّع الكلمات بنسبة عدد الحروف على [بداية، نهاية] المقطع؛ آخر كلمة تظهر قبل النهاية بـ ~18%. (`reveal_times` في الكود.)
4. المدة النهائية = **مدة الصوت**، حتى لو السكريبت قال رقم تاني. اكتب في التسليم إن الحدود مستنتجة وإنه يراجعها بالسمع.
مثال حقيقي (الحلقة دي): `B=[0,5.9,15.75,20.2,28.7,43.5,48.9,55.2]` من 12 سكتة.

**S2. قص صور المقدم** (`cutout.py`)
- خلفية خضرا: chroma key `d=g-max(r,b)`, `alpha=1-clip((d-25)/70,0,1)` + despill + أكبر component.
- خلفية بيضا: flood من الحدود على `min(rgb)>=225` + إزالة الظل الرمادي تحت الرجلين + `binary_fill_holes` (عشان التيشرت الأبيض ما يتمسحش) + erode 1px + blur 0.9.
- **نقطة تحقق: اعرضهم على خلفية حمرا** وبص. أي هالة بيضا أو ظل باقي = أعد.
- صور المقدم ثابتة: الحركة = bob + tilt ±1.6° + sparkles + أقواس حركة حوالين اليد. **متوعدش بتحريك الإيد.**

**S3. ابني الكود في طبقات** (الملحق): `lib.py` (easing/text/compositing) ← `art.py` (أجهزة/أيقونات/شخصيات) ← `scenes.py` (المشاهد + كابشن + كاميرا + FX) ← `sfx.py`+`mix.py` (الصوت) ← `chunk.py`+`run_all.sh` (الريندر).

**S4. راجع بصريًا (3 جولات+)**: اطلع 4–8 فريمات من توقيتات مختلفة في صورة واحدة. بنود الفحص (القسم 5-ج). صلّح، كرر.

**S5. الصوت**: `python3 mix.py` ← بيطلع `out/final_audio.wav` (VO + موسيقى بتتخفض تحت الصوت + SFX) بعد loudnorm على مرحلتين. **نقطة تحقق:** الناتج -14.5±0.3 LUFS و ≤ -1.5 dBTP.

**S6. الريندر: chunks مستقلة ومفصولة عن الـ shell** (ده الدرس الأهم):
```bash
chmod +x run_all.sh && setsid nohup ./run_all.sh > /dev/null 2>&1 < /dev/null &
```
- ريندر واحد طويل **وقف في النص بدون error** (حصل). كل chunk (~276 فريم) process جديد، بيكتب ملف مؤقت ثم rename، ولو موجود يتخطى → لو وقف، شغّل `run_all.sh` تاني.
- `nohup` لوحدها مش كفاية؛ استخدم `setsid`. مفيش `disown` في `/bin/sh`.
- بعد ما ينتهي (`VIDEODONE` في `out_log.txt`) اعمل المكس:
```bash
ffmpeg -y -i out/video_only.mp4 -i out/final_audio.wav -c:v copy -c:a aac -b:a 192k -ar 44100 -shortest -movflags +faststart out/<slug>.mp4
```

**S7. تحقق نهائي من الـ MP4 نفسه** (مش من الكود): `ffprobe` (المدة/الدقة/fps/streams) + `loudnorm print_format=summary` + 6 فريمات مستخرجة من الملف في contact sheet. بعدين سلّم.

## 4. المواصفات

### 4-أ. القماش والأمان
- 1080×1920، 30fps، H.264 high، yuv420p، AAC 192k–256k، faststart، المدة = مدة الصوت (45–60ث، ولو طالت اكتبها في التسليم).
- **الجودة الحقيقية = bitrate، مش المقاس.** إعدادات الـ master: `-c:v libx264 -preset medium -crf 13 -tune animation -x264-params aq-mode=3:ref=4:deblock=1,1 -pix_fmt yuv420p`. الناتج المتوقع **2.5–4 Mbps** على الرسومات دي. أي ملف تحت ~2 Mbps عند 1080×1920 = ناعم ومرفوض، حتى لو اسمه HD.
- معاينة خفيفة للمستخدم **اختيارية ومنفصلة** (مثال: 720p crf 20) وبتتسمى `*_preview.mp4`. **اللي بيتسلّم ويتقال عليه "الفيديو" هو الـ master 1080×1920.** لو عرضت معاينة، اكتب اسم الماستر تحتها في سطر. (حصل لبس من ده فعلًا.)
- **المحتوى المهم y 200–1350. الكابشن مركزه y≈1455. ولا حاجة مهمة تحت y≈1500** (واجهة المنصة). هامش 40px من الحواف. progress bar رفيع عند y≈64. chip السلسلة مركزه y≈128.

### 4-ب. الثيمات والخلفيات (متبدلة)
- ترتيب هذه الحلقة: **فاتح، فاتح، داكن (المقدم)، فاتح، داكن (الأجزاء/التقني)، فاتح، داكن (الخاتمة)** = `THEME=[0,0,1,0,1,0,1]`.
- كل مشهد شبكة مختلفة (حجم خلية/سرعة/اتجاه) = `GRID`. غبار 30 ذرة في كل مشهد.
- ألوان: أحمر `#E5262B` هو الأساسي، `#96141A` للأحمر الغامق، أبيض دافي `#F6F3ED`، حبر `#342A2C`، أصفر `#F4C430`، زمردي `#14B88A`، تيل `#1F8A8A`. **على الفاتح الأصفر يبقى GOLD `#CD8C0A` أو الأحمر؛ مفيش نص أبيض/أصفر على خلفية فاتحة.**

### 4-ج. التايبوغرافي والكابشن
- خط عربي حقيقي (Cairo/Tajawal) من ملف؛ لو مش موجود DejaVu Sans Bold + إعلان.
- الكابشن: لوحة داكنة `(48,38,40)` شفافية 232 + حد أحمر 3px، نص أبيض 58px، أقصى عرض 970، سطرين بحد أقصى. **الكلمة بتظهر بـ pop في وقتها**، والكلمات المفتاحية ملونة (أرقام=أصفر، مشكلة=أحمر، إيجابي=زمردي).
- chip علوي ثابت + progress bar بيتحطوا **بعد** حركة الكاميرا.

### 4-د. الحركة (مفيش فريم ميت)
- كاميرا: زووم 1.00→1.04 (أو العكس بالتبادل) + انجراف أفقي ±14px، بـ `cv2.warpAffine`.
- دخول: back/elastic للـ pops، slide+fade للكروت، stagger 0.14–0.6ث للقوائم.
- شخصيات: bob، رمش كل ~4.3ث (صورتين مرسومتين)، فم بيتبدل 8Hz أثناء الكلام، تغيير تعبير على الأحداث (متحمس→محبط بصدمة + اهتزاز).
- **ضربة (impact) في كل مشهد على الأقل**: حلقة توسّع + خطوط سرعة (VS) + اهتزاز 6–12px + فلاش 1–2 فريم (`IMPACTS`).
- انتقال: مسحة حمرا بحد أبيض 0.4ث على حدود المشهد (حاليًا رأسية؛ القُطرية تحسين اختياري).
- أي مشهد ساكن أكتر من ~2.5ث يتضاف له highlight بيتنقل (مع صوت tick).

### 4-هـ. الصوت
- VO من الملف كما هو. موسيقى bed (Am–F–C–G، 76 BPM، pad + bass + pluck + hats) **بتتخفض 62% تحت الصوت** (envelope follower)، مستواها ≈ 0.17×.
- **SFX: واحد لكل حركة على الشاشة** (جدول `E` في `mix.py` بالزمن المطلق): pop (ظهور)، whoosh (انتقال/دخول، مع pan متحرك)، zip+tick (حاجة بتطير وتنزل)، impact/stomp (ضربة)، riser قبل الضربات الكبيرة بـ 0.6ث، sparkle (نجاح)، tick (عدادات/قوائم)، click (ضغطة). مستواها ≈ 0.40×ذروة الصوت، مع تغيير الـ seed.
- Loudness: `loudnorm=I=-14.5:TP=-1.5:LRA=11` **على مرحلتين** (قياس ثم `measured_*` + `linear=true`). مرحلة واحدة مش دقيقة على ملف قصير.
- **كل ما تغيّر توقيت مشهد، حدّث جدول الـ SFX** (بيتحسب من `B` و`PT` فبيتحرك معاهم لو استخدمت نفس المتغيرات).

## 5. قواعد التكوين (دي اللي فرّقت بين نسختين لنفس السكريبت)
1. **بطل واحد كبير لكل مشهد** (45–60% من ارتفاع منطقة المحتوى). مقدم صغير (≈25% من الكادر) = ضعف. ميدو 650–1000px حسب المشهد، **ومش بيتغير حجمه عشوائيًا.**
2. **خط أرضي ثابت** للشخصيات (y≈1380–1400) فوق الكابشن. **الكابشن ما يغطيش جسم/رجلين شخصية.**
3. **مفيش عنصر مقطوع من الحافة.** كل sprite له هامش 30–40px حوالين الأطراف الممدودة.
4. **مفيش فراغ رأسي أكبر من ~300px** في منطقة المحتوى. لو عنصر واحد صغير: كبّره أو ضيف عناصر متحركة بمعنى (مصطلحات بتدور، فلوس بتطير، كروت بتطلع من الجهاز). **صفوف chips صغيرة ثابتة شبه الجدول = ممنوع.**
5. **عمق:** دايرة/spotlight كبيرة (80–95% من العرض) ورا البطل + ظل تحت الرجلين.
6. **أحجام النص:** label الكارت ≥ 44px، chip ≥ 40px، أيقونة ≥ 128px، على موبايل.
7. **الوش:** الراس ≥ 15–18% من طول الشخصية في لحظات الانفعال. ممنوع جسم ضخم وراس صغير.
8. **فحص تلقائي/بصري لكل مشهد:** هل في نص/ورقة/فلوس/فقاعة فوق وش؟ هل في حاجة طالعة برة [40,1040]×[40,1500]؟ هل الكابشن فوق عنصر مهم؟ هل نص على لون قريب منه (أبيض/أصفر على فاتح)؟

## 6. إزاي تكيّف الكود لحلقة جديدة
| الملف | اللي بتغيّره | اللي ما بتلمسوش |
|---|---|---|
| `scenes.py` | `B` (حدود المشاهد)، `CAPS` (الجمل+التوقيت+الألوان)، `THEME`/`GRID`، `scene1..N` (ارسم المشاهد بالعناصر الجاهزة)، `PARTS/SLOTS` لو في كروت، `IMPACTS`، نص `chip_spr` | `render_frame`, `camera`, `draw_caption`, `wipe` |
| `mix.py` | جدول `E` (SFX) + مسار الـ VO + أسماء المخرجات | الـ synth والـ loudnorm |
| `art.py` | أجهزة/أيقونات/شخصيات جديدة لو لازم | `D` wrapper |
| `assets/` | `*_cut.png` المولّدة + `CREDITS.md` | الأصول المعتمدة اللي المستخدم وافق عليها |
| `lib.py` | **مسار الخط `FONT`** | الباقي |
| `chunk.py`/`run_all.sh` | **المسار `/home/claude/reel2`** → مجلد مشروعك، وعدد الفريمات/الـ chunks | |
- كل المسارات النسبية (`assets/...`, `out/...`) بتشتغل من مجلد المشروع. غيّر `os.chdir` والمسارات المطلقة في 4 أماكن (`chunk.py`, `run_all.sh`, `mix.py`, ومسار الـ VO).
- حدّد `N` الفريمات = `round(B[-1]*30)` وعدّل قائمة بدايات الـ chunks في `run_all.sh` بالتبعية (276 فريم لكل واحد).
- معاينة سريعة: `from scenes import *; Image.fromarray(render_frame(24.6)).save('p.png')`.

## 7. أخطاء حصلت فعلًا (متكررهاش)
| العرض | السبب | الحل |
|---|---|---|
| الريندر يقف في النص بدون error | process واحد + cache بيكبر + ارتباط بالـ shell | chunks + `setsid nohup` + rename ذري |
| `TypeError: float` في `rounded_rectangle` | width float بعد الضرب في SS | `int(width*SS)` داخل الـ wrapper |
| نص كارت بيخرج برة الكارت | خط ثابت لأسماء طويلة | قيس العرض وصغّر تلقائي + `over()` بيعمل clip |
| إيد/طرف مقطوع في الـ sprite | الـ canvas أضيق من الرسمة | هامش 30–40px |
| ورق/فلوس/فقاعات فوق الوش | تموضع تقريبي | ازاحة بزاوية + مراجعة contact sheet |
| ظل رمادي/هالة بيضا حوالين المقدم | flood-fill بسيط | قاعدة الظل + erode + اعرض على خلفية ملوّنة |
| نص عربي مقطّع/معكوس | `arabic_reshaper`/`bidi` | `direction='rtl', language='ar'` + raqm |
| scipy يرفض الـ wav | هيدر غير قياسي | حوّله بـ ffmpeg الأول |
| أصفر/أبيض غير مقروء | نفس النص على خلفية فاتحة | GOLD/أحمر/حبر على الفاتح |
| الكابشن فوق رجلين الشخصية | كابشن واطي أو شخصية طويلة | الكابشن y≈1455، والرجلين ≤ 1390 |
| صوت ضعيف (-20 LUFS) | VO بس بدون معالجة | loudnorm مرحلتين → -14.5 |
| الكاميرا بتقص الـ HUD | رسم الـ HUD قبل الكاميرا | HUD والكابشن بعد الكاميرا |
| خطوط السرعة بتعدي فوق عنوان | VS قريب من العنوان | قلّل طول الخطوط أو ابعد الـ VS عن العنوان |
| "الجودة ضعيفة" رغم إن الدقة 1080 | encode bitrate واطي (~1.7 Mbps) | CRF 13 + `-tune animation` → 2.5–4 Mbps، **وقارن crop من الفريم الخام بالملف النهائي** قبل التسليم |
| المقدم المولّد ناعم في الكادر | الصور المرفوعة 286×512 | اطلب أصل ≥1000px، أو اعرضه ≤1.4× تكبير واكتب ده في التسليم |
| rembg بيقع (OOM) | alpha_matting + صورة كبيرة | صغّر لـ h≈1200–1300، ومن غير alpha_matting |
| الأصل المولّد مش راكب على الستايل | برومبت حر لكل قطعة | برومبت مقفول بالبالِت + جلسة واحدة + إعادة توليد بدل التصليح |
| الأصل المولّد له هالة/حد أبيض | تقطيع سريع | blur ألفا + قص على alpha>30 + شوفه على خلفية حمرا |
| أصل مبحوث أوقف الريندر | hotlink أو ملف مش موجود | نزّل كل الأصول في `assets/` + `CREDITS.md` |
| ترخيص صورة غير واضح | تحميل عشوائي | ممنوع: ولّد بدالها أو استخدم CC0/PD مسجّل |

## 8. قايمة القبول قبل التسليم
- [ ] 1080×1920 · 30fps · المدة = مدة الصوت · H.264 + AAC · faststart (من `ffprobe` على الملف النهائي)
- [ ] -14.5 ±0.3 LUFS و ≤ -1.5 dBTP (من `loudnorm` على الملف النهائي)
- [ ] نص عربي متصل وصحيح في كل مشهد (اتشاف فعلًا)
- [ ] ثيمات متبدلة، وكل مشهد شبكته مختلفة عن جاره
- [ ] كل مشهد فيه حركة + ضربة واحدة على الأقل، والـ HUD ثابت وغير مقطوع
- [ ] كل مشهد اتراجع بصريًا (مفيش نص فوق وش، مفيش عنصر مقطوع، مفيش فراغ كبير)
- [ ] SFX عند كل حركة، وموسيقى بتتخفض تحت الصوت
- [ ] مكان اللوجو/الاسم واضح، والخط المؤقت (لو مؤقت) معلن
- [ ] **bitrate ≥ 2.5 Mbps** على الماستر (HD حقيقي، مش اسم فقط) + مقارنة crop خام مقابل crop من الملف
- [ ] كل أصل مولّد/مبحوث: متسق مع الستايل-لوك، مفحوص على خلفية متباينة وبالحجم النهائي
- [ ] `assets/CREDITS.md` موجود لو في أصل مبحوث، والأصول المولّدة معلنة في رسالة التسليم

## 9. رسالة التسليم (قالب — 8–10 سطور بالمصري)
1. اسم الملف + المواصفات (مدة/دقة/LUFS من القياس الفعلي).
2. مشهد بمشهد في سطر.
3. **اللي مش متأكد منه:** حدود المشاهد مستنتجة، الخط، الاسم/اللوجو، أي قيد في حركة المقدم.
4. **الأصول:** أي حاجة مولّدة أو متحمّلة من النت (واسم اللترخيص) — وجملة واحدة إن الستايل متسق معاها.
5. 2–3 حاجات هتحسّنها بعد كده.

## 10. قيود معروفة / تحسينات ممكنة
- **حدود التوليد:** الـ AI بيعمل صورة واحدة مش سبرايت شيت متحرك؛ الحركة لازم تتضاف بالكود (bob/دوران/دخول). ومش بيحافظ على أصل واحد من زاوية تانية بدقة — لو محتاج وضعيتين لنفس الجهاز، ولّدهم في نفس الجلسة وبنفس البرومبت.
- الخط DejaVu لحد ما يتوفر Cairo/Tajawal. الانتقال رأسي مش قُطري. موسيقى بسيطة مصنّعة. صور المقدم ثابتة (مفيش تحريك لإيده). الشخصيات الثانوية flat-vector أبسط من رسمة المقدم.
- لو عايز مقدم متحرك أكتر: اطلب أوضاع إضافية (إيد مرفوعة/نازلة، فم مفتوح/مقفول) كصور منفصلة وبدّل بينها بالزمن.

---------------------------------------------------------------------
## 11. مصادر العناصر: كود / توليد / بحث

> إحنا مش بنمنع التوليد ولا البحث. إحنا بنمنع **الستايل المهلهل**. القاعدة الحاكمة: المشاهد بيبان نضيف لما كل عنصر — مرسوم أو مولّد أو محمّل — يبقى بيتكلم نفس اللغة: نفس البالِت، نفس سماكة الخطوط، نفس الإضاءة المسطحة.

### 11-أ. السلّم (اختر بالأولوية دي)
| الأولوية | المصدر | إمتى |
|---|---|---|
| 1 | **كود** (`art.py`, `D` wrapper) | نص، كابشن، chips، كروت، أشرطة/جداول/عدادات، أسهم، خلفيات، انتقالات، أي أيقونة صغيرة متكررة. **أسرع وأحدّ وبيتحرك كود** |
| 2 | **توليد AI** | البطل اللي الجمهور بيبصلّه: جهاز، منتج، شخصية، سيت أب كامل، مكوّن (رام/هارد/كارت). برضه الخلفيات الغنية |
| 3 | **بحث في الإنترنت** | أصل حقيقي مفيش بديل ليه: لوجو رسمي، صورة منتج، علامة تجارية، صورة خبرية |
| ❌ | stock عشوائي | ستايل مختلف، ترخيص مش معروف، واترمارك، لقطة فيها وشوش مش لازمة |

**قاعدة الحدود:** الكود مش بيعمل حاجة واقعية حلوة، والـ AI مش بيعمل حاجة مضبوطة بالبكسل ولا متحركة. **استخدم الاتنين في نفس المشهد:** التوليد للبطل، الكود للكارت/الشريط/الكابشن/النجوم حواليه.

### 11-ب. خط التوليد (5 خطوات — اتبعها بالترتيب)
1. **برومبت مقفول (قالب)** — مش برومبت حر:
   ```
   Flat vector illustration of <SUBJECT> seen from <ANGLE>,
   <2–3 تفاصيل مادية بسيطة>, clean thick dark outlines, cel-shaded flat colors,
   no gradients, no text, no logos, no watermark,
   isolated on a pure white background, centered, product illustration style
   ```
   وحطّ البالِت في البرومبت لو الأداة بتفهمها: "dark charcoal #17161b body, red #e5262b accent, dark-green screen with teal bars and one yellow dot".
2. **جلسة واحدة لكل الفيديو** — كل قطع الأصول تتولد ورا بعض بنفس القالب، وإلا هتلاقي واحدة "شبه 3D" والتانية "كرتون". لو قطعة طلعت برة الستايل: **ولّدها تاني، متصلحهاش بالكود.** (استثناء: بقع بكسل صغيرة — شيل لوجو/نقطة بإليبس بلون مسحوب من المكان، زي ما اتعمل مع لوجو التفاحة على اللابتوب.)
3. **قص الخلفية** (`rembg`):
   ```python
   from rembg import remove, new_session
   s=new_session('u2net')
   src=Image.open('assets/x.png').convert('RGB'); w,h=src.size
   if h>1200: src=src.resize((int(w*1200/h),1200),Image.LANCZOS)   # قبل التقطيع!
   out=remove(src,session=s)          # بدون alpha_matting (بيقع OOM على 2GB)
   # blur ألفا 0.5–0.7 → قص على alpha>30 +2px → assets/x_cut.png
   ```
4. **لودر + كاش** في `scenes.py`:
   ```python
   ARTD={}
   def ART(name,h):
       k=(name,h)
       if k not in ARTD: ARTD[k]=load_png(name+'_cut',h)
       return ARTD[k]
   ```
5. **إدخال بحركة** — ممنوع لصق ساكن:
   ```python
   paste(fr,ART('gen_pc',560),cx,1010,scale=k,alpha=min(1,k))              # مركز
   paste(fr,ART('gen_laptop',300),lx,1272+(1-lk)*90,anchor=(0.5,1.0))      # قاعد على الأرض
   ```
   + ظل (`shadow_ell`) + دخول بـ `e_back`/`e_io` + bob أو دوران ±7°. **أي أصل ثابت أكتر من 2.5ث = فريم ميت.**

### 11-ج. بوابات الجودة (قبل ما الأصل يدخل الكادر)
- [ ] اتشاف **على خلفية حمرا أو سودا** → مفيش هالة بيضا، مفيش حد زغبي، مفيش أثر ظل.
- [ ] اتشاف **بالحجم النهائي في الكادر** (مش 1:1 في الفيوَر).
- [ ] الأسلوب متسق مع الأصول التانية في نفس الفيديو (سماكة الخطوط + البالِت + الإضاءة).
- [ ] الفريم الكامل اتراجع: الأصل مش حاطط على كابشن/وش/نص، ومش مقطوع من الحافة، وفيه هامش 30–40px.
- الترتيب الإلزامي: **أصل واحد → فريم واحد → 3 فريمات → contact sheet → ريندر كامل.**

### 11-د. البحث في الإنترنت
- التراخيص المقبولة: **CC0 / Public Domain / OFL / Unsplash / Pexels / Wikimedia (مع النسبة)**. أو SVG بسيط يتلوّن بالكود.
- **نزّل الملف في `assets/`** — ممنوع hotlink أو تحميل وقت الريندر.
- سجّل كل أصل في **`assets/CREDITS.md`**: `الاسم — الرابط — الترخيص — التاريخ`.
- **ترخيص مش واضح = ممنوع.** ولّد بدالها.
- صور المستخدم: خُد منها **الهوية** فقط (شكل/لبس/ستايل)، ومتحوّلهاش لستايل تاني من غير ما تقول.
- لو الأداة بتجيب صور بحث: راجع الصورة بنفسك قبل الاستخدام (مش كل نتيجة مطابقة للوصف).

### 11-هـ. ستايل-لوك (البالِت المرجعي)
| الاستخدام | اللون |
|---|---|
| حبر / جسم الجهاز | `INK (24,22,26)` · `INK2 (52,42,44)` |
| أساسي / تحذير | `RED (229,38,43)` · `DRED (150,20,26)` |
| ورقي / نص على غامق | `WHITE (246,243,237)` |
| إيجابي | `EMER (20,184,138)` |
| ثانوي | `TEAL (31,138,138)` |
| تمييز | `YEL (244,196,48)` · `GOLD (205,140,10)` |

- **شاشات الأجهزة في كل أصل مولّد = شاشة خضرا غامقة + أشرطة تيل + نقطة صفرا واحدة.** دي الخيط اللي بيربط رسومات الكود بالتوليد، ولو مش موجودة الأجهزة هتبان من عالم تاني.
- الإضاءة مسطحة، الظل inline، مفيش gradients ولا blur ناعم.

### 11-و. الأصوات (لو بتعمل TTS)
- ولّد **جولتين على الأقل** من نفس سطر السكريبت (زوجين = 4 بروفايلات) وسيب المستخدم يختار.
- اطلب اللهجة صريحة: `language="ar-EG"` (طلب اللهجة شرط صارم؛ لو فشل ارجع لـ `ar` وقول للمستخدم).
- بعد الاختيار: **صوت واحد لكل الجمل** + `atempo` واحد ثابت (1.15–1.22×) + نفس سلسلة المعالجة.
- كل ما تغيّر الصوت → `build_vo.py` + `mix.py` + ريندر كامل. (التوقيتات بتتغير، و`B` بيتحسب، متعملهاش يدوي.)

### 11-پ. لو المستخدم رفض أصل
- اطلب منه **النسخة الأصلية بدقة أعلى** (≥1000px للارتفاع) — أغلب اللي بيترفع بيبقى thumbnail 286×512 وبيبان ناعم في الكادر.
- لحد ما توصل: اعرضه **≤1.4× تكبير** وقلّل حجمه في المشهد، وقول ده صريح في التسليم.
- متحاولش "تحسّن" صورة صغيرة بالـ sharpen وخلاص — النتيجة بتزعّج.

---------------------------------------------------------------------
# APPENDIX — REFERENCE SOURCE (اللي اشتغل فعلًا)
> كل الملفات تحت في مجلد مشروع واحد مع `assets/` (صور المقدم المقصوصة: `medo_wave.png`, `medo_think.png`, `medo_point.png`) و`out/`.
> `scenes.py` مرتبط بسكريبت حلقة اللابتوب؛ اعتبره **قالب**: خد منه البنية والعناصر وغيّر المشاهد.


## FILE: lib.py
```python
import numpy as np, cv2, math, functools
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'   # swap with Cairo-Bold.ttf if you have it
BLACK=(10,10,12); INK=(24,22,26); RED=(229,38,43); DRED=(150,20,26); WHITE=(246,243,237)
EMER=(20,184,138); TEAL=(31,138,138); YEL=(244,196,48); GRAY=(120,120,128); LGRAY=(205,205,212)
SS=3
# ---------- easing ----------
def clamp(x,a=0,b=1): return max(a,min(b,x))
def prog(t,a,b): return clamp((t-a)/(b-a)) if b>a else (1.0 if t>=a else 0.0)
def e_out(x): return 1-(1-x)**3
def e_io(x): return 3*x*x-2*x**3
def e_back(x,s=1.9): x=x-1; return 1+(s+1)*x**3+s*x**2
def e_elastic(x):
    if x<=0: return 0
    if x>=1: return 1
    return 1-math.exp(-7*x)*math.cos(11*x)
def lerp(a,b,x): return a+(b-a)*x
# ---------- text ----------
@functools.lru_cache(maxsize=2000)
def text_sprite(txt,size,color=(255,255,255),rtl=True,stroke=0,scolor=(0,0,0)):
    f=ImageFont.truetype(FONT,size,layout_engine=ImageFont.Layout.RAQM)
    kw=dict(direction='rtl',language='ar') if rtl else dict(direction='ltr')
    d0=ImageDraw.Draw(Image.new('L',(4,4)))
    x0,y0,x1,y1=d0.textbbox((0,0),txt,font=f,stroke_width=stroke,**kw)
    pad=6+stroke
    im=Image.new('RGBA',(x1-x0+2*pad,y1-y0+2*pad),(0,0,0,0))
    ImageDraw.Draw(im).text((pad-x0,pad-y0),txt,font=f,fill=color+(255,),stroke_width=stroke,stroke_fill=scolor+(255,),**kw)
    return prem(np.array(im))
def prem(a):
    a=a.astype(np.float32); a[...,:3]*=a[...,3:4]/255.0; return a
# ---------- sprite drawing (supersampled) ----------
class D:
    def __init__(s,w,h):
        s.w,s.h=w,h; s.im=Image.new('RGBA',(w*SS,h*SS),(0,0,0,0)); s.d=ImageDraw.Draw(s.im)
    def _b(s,b): return [v*SS for v in b]
    def rect(s,b,fill=None,outline=None,width=0): s.d.rectangle(s._b(b),fill=fill,outline=outline,width=int(width*SS))
    def rrect(s,b,r,fill=None,outline=None,width=0): s.d.rounded_rectangle(s._b(b),r*SS,fill=fill,outline=outline,width=int(width*SS))
    def ell(s,b,fill=None,outline=None,width=0): s.d.ellipse(s._b(b),fill=fill,outline=outline,width=int(width*SS))
    def poly(s,pts,fill=None,outline=None,width=0):
        p=[(x*SS,y*SS) for x,y in pts]; s.d.polygon(p,fill=fill)
        if outline: s.d.line(p+[p[0]],fill=outline,width=int(width*SS),joint='curve')
    def line(s,pts,fill,width,round_=True):
        p=[(x*SS,y*SS) for x,y in pts]; s.d.line(p,fill=fill,width=int(width*SS),joint='curve')
        if round_:
            r=width*SS/2
            for x,y in (p[0],p[-1]): s.d.ellipse([x-r,y-r,x+r,y+r],fill=fill)
    def arc(s,b,a0,a1,fill,width): s.d.arc(s._b(b),a0,a1,fill=fill,width=int(width*SS))
    def circ(s,cx,cy,r,fill=None,outline=None,width=0): s.ell((cx-r,cy-r,cx+r,cy+r),fill,outline,width)
    def text(s,xy,txt,size,fill,rtl=False,anchor='mm'):
        f=ImageFont.truetype(FONT,size*SS,layout_engine=ImageFont.Layout.RAQM)
        kw=dict(direction='rtl',language='ar') if rtl else {}
        s.d.text((xy[0]*SS,xy[1]*SS),txt,font=f,fill=fill,anchor=anchor,**kw)
    def done(s):
        im=s.im.resize((s.w,s.h),Image.LANCZOS); return prem(np.array(im))
def load_png(name,height):
    im=cv2.imread(f'assets/{name}.png',cv2.IMREAD_UNCHANGED)
    w=int(im.shape[1]*height/im.shape[0])
    im=cv2.resize(im,(w,height),interpolation=cv2.INTER_AREA)
    im=cv2.cvtColor(im,cv2.COLOR_BGRA2RGBA); return prem(im)
# ---------- compositing ----------
def paste(fr,spr,cx,cy,scale=1.0,rot=0.0,alpha=1.0,anchor=(0.5,0.5),flipx=False,sy=None):
    if alpha<=0.003 or scale<=0.003: return
    h,w=spr.shape[:2]; ax,ay=anchor[0]*w,anchor[1]*h
    sxs=scale*(-1 if flipx else 1); sys_=scale if sy is None else sy
    c,sn=math.cos(math.radians(rot)),math.sin(math.radians(rot))
    M=np.array([[c*sxs,-sn*sys_,0],[sn*sxs,c*sys_,0]],np.float32)
    M[0,2]=cx-(M[0,0]*ax+M[0,1]*ay); M[1,2]=cy-(M[1,0]*ax+M[1,1]*ay)
    pts=np.array([[0,0],[w,0],[w,h],[0,h]],np.float32)
    dst=pts@M[:,:2].T+M[:,2]
    x0=max(int(dst[:,0].min())-1,0); x1=min(int(dst[:,0].max())+2,W)
    y0=max(int(dst[:,1].min())-1,0); y1=min(int(dst[:,1].max())+2,H)
    if x1<=x0 or y1<=y0: return
    M2=M.copy(); M2[0,2]-=x0; M2[1,2]-=y0
    wp=cv2.warpAffine(spr,M2,(x1-x0,y1-y0),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
    a=wp[...,3:4]/255.0*alpha
    roi=fr[y0:y1,x0:x1]
    roi[:]=np.clip(wp[...,:3]*alpha+roi*(1-a),0,255)
def fill_rect(fr,x0,y0,x1,y1,color,alpha=1.0):
    x0,y0,x1,y1=max(int(x0),0),max(int(y0),0),min(int(x1),W),min(int(y1),H)
    if x1<=x0 or y1<=y0: return
    roi=fr[y0:y1,x0:x1]; roi[:]=roi*(1-alpha)+np.array(color,np.float32)*alpha
# ---------- reusable sprites ----------
@functools.lru_cache(maxsize=None)
def circle_spr(r,color,glow=0):
    pad=glow*2+4; d=D(2*r+2*pad,2*r+2*pad)
    if glow:
        g=Image.new('RGBA',d.im.size,(0,0,0,0)); gd=ImageDraw.Draw(g)
        gd.ellipse([pad*SS,pad*SS,(pad+2*r)*SS,(pad+2*r)*SS],fill=color+(150,))
        g=g.filter(__import__('PIL.ImageFilter',fromlist=['x']).GaussianBlur(glow*SS*0.8)); d.im.alpha_composite(g)
    d.circ(pad+r,pad+r,r,fill=color); return d.done()
@functools.lru_cache(maxsize=None)
def sparkle(r,color=(255,255,255)):
    d=D(r*2+4,r*2+4); c=r+2
    pts=[(c,c-r),(c+r*0.18,c-r*0.18),(c+r,c),(c+r*0.18,c+r*0.18),(c,c+r),(c-r*0.18,c+r*0.18),(c-r,c),(c-r*0.18,c-r*0.18)]
    d.poly(pts,fill=color); return d.done()
@functools.lru_cache(maxsize=None)
def pill(w,h,color,alpha=255,r=None):
    d=D(w,h); d.rrect((0,0,w,h),r if r else h//2,fill=color+(alpha,)); return d.done()
@functools.lru_cache(maxsize=None)
def bill(w=150):
    h=int(w*0.55); d=D(w,h)
    d.rrect((0,0,w,h),10,fill=(60,170,110),outline=(30,100,64),width=4)
    d.circ(w/2,h/2,h*0.3,fill=(110,205,150),outline=(30,100,64),width=3); d.text((w/2,h/2),'EGP',int(h*0.26),(30,100,64))
    d.rrect((10,10,34,22),4,fill=(110,205,150)); d.rrect((w-34,h-22,w-10,h-10),4,fill=(110,205,150)); return d.done()
@functools.lru_cache(maxsize=None)
def checkmark(s,color=EMER,bg=True):
    d=D(s,s)
    if bg: d.circ(s/2,s/2,s/2-2,fill=color)
    d.line([(s*.27,s*.52),(s*.44,s*.69),(s*.74,s*.34)],(255,255,255) if bg else color,s*.11); return d.done()
@functools.lru_cache(maxsize=None)
def crossmark(s,color=RED):
    d=D(s,s); d.circ(s/2,s/2,s/2-2,fill=color)
    d.line([(s*.3,s*.3),(s*.7,s*.7)],(255,255,255),s*.11); d.line([(s*.7,s*.3),(s*.3,s*.7)],(255,255,255),s*.11); return d.done()
@functools.lru_cache(maxsize=None)
def bubble(w,h,color=(255,255,255),tail='bl',alpha=255,outline=None):
    d=D(w+40,h+50); d.rrect((20,10,20+w,10+h),h*0.28 if h<200 else 40,fill=color+(alpha,),outline=outline,width=4 if outline else 0)
    if tail=='bl': d.poly([(60,10+h-4),(40,10+h+34),(110,10+h-4)],fill=color+(alpha,))
    elif tail=='br': d.poly([(w-70,10+h-4),(w-10,10+h+34),(w+0,10+h-4)],fill=color+(alpha,))
    elif tail=='bc': d.poly([(w/2-20,10+h-4),(w/2+20,10+h+34),(w/2+50,10+h-4)],fill=color+(alpha,))
    return d.done()

```


## FILE: art.py
```python
import functools, math
from lib import *
from PIL import ImageFilter
OL=(18,16,20)
# ================= DEVICES =================
@functools.lru_cache(maxsize=None)
def laptop(w=520,screen='glow',tilt_open=True):
    lh=int(w*0.62); bh=int(w*0.05); tot=lh+bh+6; d=D(int(w*1.1),tot); ox=int(w*0.05)
    d.rrect((ox,0,ox+w,lh),w*0.035,fill=(34,34,40),outline=OL,width=4)
    sx0,sy0,sx1,sy1=ox+w*0.035,w*0.035,ox+w*0.965,lh-w*0.035
    col={'glow':(14,60,52),'bad':(70,14,18),'blank':(22,24,30),'dark':(16,16,20)}[screen]
    d.rrect((sx0,sy0,sx1,sy1),w*0.012,fill=col)
    cx,cy=(sx0+sx1)/2,(sy0+sy1)/2
    if screen=='glow':
        for i,(ww,c) in enumerate([(0.55,EMER),(0.38,TEAL),(0.46,(60,90,86))]):
            y=sy0+(sy1-sy0)*(0.22+i*0.17); d.rrect((sx0+w*0.06,y,sx0+w*0.06+w*ww,y+w*0.045),6,fill=c)
        d.circ(sx1-w*0.15,sy0+w*0.13,w*0.055,fill=YEL)
    elif screen=='bad':
        d.circ(cx,cy,w*0.15,fill=RED); d.line([(cx-w*.07,cy-w*.07),(cx+w*.07,cy+w*.07)],(255,255,255),w*.035); d.line([(cx+w*.07,cy-w*.07),(cx-w*.07,cy+w*.07)],(255,255,255),w*.035)
    elif screen=='blank': d.circ(cx,cy,w*0.05,fill=(70,74,84))
    d.rrect((0,lh+2,w*1.1,lh+2+bh),bh/2,fill=(196,196,204),outline=OL,width=3)
    d.rrect((w*0.55-w*0.09,lh+2,w*0.55+w*0.09,lh+2+bh*0.5),bh/3,fill=(150,150,158))
    return d.done()
@functools.lru_cache(maxsize=None)
def desktop(w=420):
    h=int(w*1.0); d=D(int(w*1.25),h+10)
    mw=int(w*0.78); mh=int(mw*0.6)
    d.rrect((0,0,mw,mh),12,fill=(34,34,40),outline=OL,width=4)
    d.rrect((14,14,mw-14,mh-14),6,fill=(14,60,52))
    for i,(ww,c) in enumerate([(0.5,EMER),(0.34,TEAL)]): d.rrect((34,36+i*48,34+mw*ww,60+i*48),6,fill=c)
    d.rect((mw/2-18,mh,mw/2+18,mh+int(w*0.14)),fill=(150,150,158),outline=OL,width=3)
    d.rrect((mw/2-int(w*0.18),mh+int(w*0.14),mw/2+int(w*0.18),mh+int(w*0.17)),8,fill=(196,196,204),outline=OL,width=3)
    kx=mw/2-int(w*0.3)
    d.rrect((kx,mh+int(w*0.24),kx+int(w*0.6),mh+int(w*0.31)),8,fill=(60,60,68),outline=OL,width=3)
    tx=int(w*0.84); th=int(w*0.88)
    d.rrect((tx,int(w*0.08),tx+int(w*0.4),int(w*0.08)+th),12,fill=(44,44,52),outline=OL,width=4)
    d.circ(tx+int(w*0.2),int(w*0.2),int(w*0.05),fill=RED)
    for i in range(3): d.rrect((tx+int(w*0.07),int(w*0.34)+i*int(w*0.06),tx+int(w*0.33),int(w*0.34)+i*int(w*0.06)+8),4,fill=(80,80,90))
    return d.done()
# ================= PART ICONS (200x200) =================
@functools.lru_cache(maxsize=None)
def icon(kind,s=170,color=WHITE):
    d=D(s,s); c=s/2; k=s/200.0; ac=RED
    if kind=='cpu':
        for i in range(5):
            p=40+i*30*1
            d.line([(p*k,22*k),(p*k,40*k)],color,6*k,False); d.line([(p*k,160*k),(p*k,178*k)],color,6*k,False)
            d.line([(22*k,p*k),(40*k,p*k)],color,6*k,False); d.line([(160*k,p*k),(178*k,p*k)],color,6*k,False)
        d.rrect((40*k,40*k,160*k,160*k),16*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((72*k,72*k,128*k,128*k),8*k,fill=ac)
    elif kind=='ram':
        d.rrect((12*k,62*k,188*k,138*k),8*k,fill=(44,44,52),outline=color,width=6*k)
        for i in range(4): d.rrect(((28+i*38)*k,78*k,(54+i*38)*k,106*k),4*k,fill=ac if i%2==0 else color)
        for i in range(12): d.rect(((20+i*13.5)*k,138*k,(26+i*13.5)*k,152*k),fill=YEL)
    elif kind=='ssd':
        d.rrect((26*k,50*k,174*k,150*k),12*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((44*k,68*k,100*k,100*k),6*k,fill=ac); d.rrect((112*k,68*k,156*k,100*k),6*k,fill=color)
        d.rrect((44*k,112*k,156*k,126*k),6*k,fill=GRAY); d.circ(158*k,134*k,6*k,fill=EMER)
    elif kind=='display':
        d.rrect((14*k,34*k,186*k,142*k),12*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((28*k,48*k,172*k,128*k),6*k,fill=TEAL)
        d.poly([(28*k,128*k),(80*k,86*k),(110*k,112*k),(132*k,94*k),(172*k,128*k)],fill=EMER)
        d.circ(142*k,70*k,10*k,fill=YEL); d.rrect((70*k,150*k,130*k,162*k),5*k,fill=color)
    elif kind=='gpu':
        d.rrect((10*k,56*k,190*k,142*k),10*k,fill=(44,44,52),outline=color,width=6*k)
        for fx in (62,128):
            d.circ(fx*k,99*k,28*k,fill=(30,30,36),outline=color,width=5*k)
            for a in range(0,360,72):
                d.line([(fx*k,99*k),((fx+20*math.cos(math.radians(a)))*k,(99+20*math.sin(math.radians(a)))*k)],ac,5*k,False)
            d.circ(fx*k,99*k,5*k,fill=color)
        for i in range(10): d.rect(((22+i*10)*k,142*k,(27+i*10)*k,156*k),fill=YEL)
    elif kind=='battery':
        d.rrect((14*k,56*k,170*k,144*k),14*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((170*k,82*k,188*k,118*k),5*k,fill=color)
        for i in range(3): d.rrect(((28+i*42)*k,70*k,(60+i*42)*k,130*k),6*k,fill=EMER)
        d.poly([(104*k,62*k),(84*k,104*k),(100*k,104*k),(92*k,142*k),(124*k,92*k),(106*k,92*k)],fill=YEL,outline=OL,width=2*k)
    return d.done()
# ================= PEOPLE =================
def _hair(d,cx,cy,r,col,style='curly'):
    if style=='curly':
        import random; rnd=random.Random(7)
        for a in range(190,351,16):
            x=cx+(r+4)*math.cos(math.radians(a)); y=cy+(r+4)*math.sin(math.radians(a))*0.95
            d.circ(x,y,r*0.40,fill=col,outline=OL,width=3)
        for a in range(205,336,22): d.circ(cx+(r*0.62)*math.cos(math.radians(a)),cy+(r*0.7)*math.sin(math.radians(a)),r*0.42,fill=col)
        d.circ(cx,cy-r*0.55,r*0.7,fill=col)
    else:
        d.ell((cx-r-6,cy-r-12,cx+r+6,cy+r*0.35),fill=col,outline=OL,width=3)
def _face(d,cx,cy,expr,skin,blink=False):
    ex=34; ey=-4
    E=(20,16,20)
    def eye(x,y,kind):
        if blink:
            d.line([(x-13,y+2),(x+13,y+2)],E,5); return
        if kind=='open': d.ell((x-12,y-17,x+12,y+17),fill=E); d.circ(x+4,y-7,5,fill=(255,255,255))
        elif kind=='big': d.ell((x-15,y-21,x+15,y+21),fill=E); d.circ(x+5,y-9,7,fill=(255,255,255)); d.circ(x-5,y+8,3.5,fill=(255,255,255))
        elif kind=='half': d.ell((x-12,y-12,x+12,y+14),fill=E); d.rect((x-14,y-14,x+14,y-3),fill=skin); d.line([(x-14,y-3),(x+14,y-3)],OL,4,False); d.circ(x+3,y+3,3.5,fill=(255,255,255))
        elif kind=='side': d.ell((x-12,y-16,x+12,y+16),fill=(255,255,255),outline=OL,width=3); d.circ(x+5,y-6,7,fill=E)
    def brow(x0,y0,x1,y1,w=7): d.line([(x0,y0),(x1,y1)],E,w)
    L,R=cx-ex,cx+ex
    if expr=='excited':
        eye(L,cy+ey,'big'); eye(R,cy+ey,'big')
        brow(L-16,cy-34,L+14,cy-40); brow(R-14,cy-40,R+16,cy-34)
        d.rrect((cx-26,cy+30,cx+26,cy+66),22,fill=(95,22,30),outline=OL,width=3); d.rect((cx-22,cy+33,cx+22,cy+42),fill=(255,255,255)); d.ell((cx-14,cy+50,cx+14,cy+68),fill=(222,80,96))
        d.circ(L-12,cy+28,11,fill=(236,120,110)); d.circ(R+12,cy+28,11,fill=(236,120,110))
    elif expr=='frustrated':
        eye(L,cy+ey+4,'half'); eye(R,cy+ey+4,'half')
        brow(L-18,cy-44,L+14,cy-28,8); brow(R+18,cy-44,R-14,cy-28,8)
        d.arc((cx-24,cy+44,cx+24,cy+84),200,340,E,6)
        for i in (-18,0,18): d.line([(cx+i,cy-96),(cx+i,cy-70)],(60,60,90),4,False)
        d.ell((R+30,cy-20,R+46,cy+8),fill=(120,200,240),outline=OL,width=2); d.poly([(R+38,cy-36),(R+30,cy-16),(R+46,cy-16)],fill=(120,200,240))
    elif expr=='confused':
        eye(L,cy+ey,'side'); eye(R,cy+ey,'side')
        brow(L-16,cy-30,L+14,cy-38); brow(R-14,cy-46,R+16,cy-30)
        d.line([(cx-22,cy+54),(cx-10,cy+46),(cx+2,cy+56),(cx+14,cy+46),(cx+24,cy+54)],E,6)
        d.ell((L-48,cy-12,L-32,cy+16),fill=(120,200,240),outline=OL,width=2); d.poly([(L-40,cy-28),(L-48,cy-8),(L-32,cy-8)],fill=(120,200,240))
    elif expr in('talk1','talk2'):
        eye(L,cy+ey,'open'); eye(R,cy+ey,'open'); brow(L-16,cy-36,L+14,cy-40); brow(R-14,cy-40,R+16,cy-36)
        if expr=='talk1': d.ell((cx-20,cy+36,cx+20,cy+72),fill=(95,22,30),outline=OL,width=3); d.ell((cx-11,cy+54,cx+11,cy+70),fill=(222,80,96))
        else: d.ell((cx-14,cy+44,cx+14,cy+62),fill=(95,22,30),outline=OL,width=3)
    elif expr=='confident':
        eye(L,cy+ey,'open'); eye(R,cy+ey,'open'); brow(L-16,cy-36,L+14,cy-40); brow(R-14,cy-46,R+16,cy-40)
        d.arc((cx-30,cy+22,cx+30,cy+70),20,160,E,7); d.circ(L-12,cy+28,10,fill=(236,120,110)); d.circ(R+12,cy+28,10,fill=(236,120,110))
    else: # smile
        eye(L,cy+ey,'open'); eye(R,cy+ey,'open'); brow(L-16,cy-36,L+14,cy-40); brow(R-14,cy-40,R+16,cy-36)
        d.arc((cx-28,cy+20,cx+28,cy+66),20,160,E,7)
@functools.lru_cache(maxsize=None)
def person(shirt,expr='smile',pose='stand',skin=(196,138,96),pants=(40,42,52),hair=(26,20,22),hairstyle='curly',tie=None,collar=None,blink=False):
    w,h=400,780; d=D(w,h); cx,cy=200,150
    arm_col=shirt
    def arm(pts,hand):
        d.line(pts,OL,60); d.line(pts,arm_col,52); d.circ(hand[0],hand[1],30,fill=OL); d.circ(hand[0],hand[1],26,fill=skin)
    # legs
    for x in (155,245):
        d.rrect((x-42,470,x+42,730),30,fill=pants,outline=OL,width=4); d.rrect((x-50,716,x+50,758),20,fill=(26,26,30),outline=OL,width=4)
    # back arms (drawn before torso for some poses)
    poses={
     'stand':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(316,410),(314,500)],(314,512))],
     'hold':[([(104,290),(70,410),(150,440)],(160,446)),([(296,290),(330,410),(250,440)],(240,446))],
     'shrug':[([(104,290),(52,400),(40,330)],(38,316)),([(296,290),(348,400),(360,330)],(362,316))],
     'talk':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(350,380),(360,296)],(362,270))],
     'paper':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(350,350),(318,260)],(316,240))],
     'scratch':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(356,210),(300,100)],(292,88))],
     'cross':[([(104,290),(90,400),(190,380)],(200,384)),([(296,290),(310,400),(210,380)],(200,384))],
    }
    arms=poses[pose]
    # torso
    d.rrect((84,246,316,500),70,fill=shirt,outline=OL,width=4)
    if collar: d.poly([(170,246),(230,246),(200,300)],fill=collar,outline=OL,width=3)
    if tie: d.poly([(190,296),(210,296),(218,380),(200,404),(182,380)],fill=tie,outline=OL,width=3)
    for pts,hand in arms: arm(pts,hand)
    # neck + head
    d.rrect((172,214,228,268),16,fill=skin,outline=OL,width=3)
    _hair(d,cx,cy,100,hair,hairstyle) if hairstyle=='curly' else None
    d.circ(cx,cy,100,fill=skin,outline=OL,width=4)
    d.circ(cx-100,cy+6,16,fill=skin,outline=OL,width=3); d.circ(cx+100,cy+6,16,fill=skin,outline=OL,width=3)
    if hairstyle=='curly':
        for a in range(205,336,26): d.circ(cx+(86)*math.cos(math.radians(a)),cy+(78)*math.sin(math.radians(a)),26,fill=hair)
        d.rect((cx-88,cy-6-70,cx+88,cy-60),fill=None)
    else:
        d.poly([(cx-102,cy-10),(cx-96,cy-72),(cx-40,cy-104),(cx+40,cy-108),(cx+98,cy-70),(cx+102,cy-10),(cx+70,cy-46),(cx-20,cy-62),(cx-70,cy-36)],fill=hair,outline=OL,width=3)
    _face(d,cx,cy,expr,skin,blink)
    return d.done()
@functools.lru_cache(maxsize=None)
def paper_spec(w=200,checks=5):
    h=int(w*1.25); d=D(w,h+10)
    d.rrect((0,0,w,h),10,fill=(250,248,242),outline=OL,width=4)
    for i in range(5):
        y=26+i*int(h/6.4); d.rrect((w*0.30,y,w*0.88,y+10),4,fill=(190,190,196))
        if i<checks: d.line([(w*0.08,y+6),(w*0.14,y+14),(w*0.24,y-2)],EMER,5)
    return d.done()
@functools.lru_cache(maxsize=None)
def follow_button(w=520,h=150,pressed=False,done=False):
    d=D(w,h); col=(60,60,68) if done else RED
    d.rrect((0,0,w,h),h*0.5,fill=col,outline=(255,255,255) if not done else (120,120,128),width=4)
    if done: d.line([(w*0.16,h*.52),(w*0.2,h*.66),(w*0.28,h*.36)],EMER,10); d.text((w*0.62,h*.5),'تمت المتابعة',46,WHITE,rtl=True)
    else:
        d.circ(w*0.17,h/2,h*0.28,fill=(255,255,255)); d.line([(w*0.17-15,h/2),(w*0.17+15,h/2)],RED,8); d.line([(w*0.17,h/2-15),(w*0.17,h/2+15)],RED,8)
        d.text((w*0.60,h*.5),'تابع',64,WHITE,rtl=True)
    return d.done()
@functools.lru_cache(maxsize=None)
def cursor(s=90):
    d=D(s,s); d.poly([(8,6),(8,62),(24,48),(36,76),(48,70),(36,44),(58,44)],fill=(255,255,255),outline=OL,width=4); return d.done()

```


## FILE: scenes.py
```python
import math, functools, random
from art import *
B=[0,5.9,15.75,20.2,28.7,43.5,48.9,55.2]
FPS=30
def over(dst,src,x,y):
    h,w=src.shape[:2]; H_,W_=dst.shape[:2]
    sx0=max(0,-x); sy0=max(0,-y); x=max(x,0); y=max(y,0)
    src=src[sy0:,sx0:]; h,w=src.shape[:2]; h=min(h,H_-y); w=min(w,W_-x); src=src[:h,:w]
    if h<=0 or w<=0: return
    roi=dst[y:y+h,x:x+w]; roi[:]=src+roi*(1-src[...,3:4]/255.0)
# ---------- background ----------
def make_bg():
    yy=np.linspace(0,1,H)[:,None,None]
    base=np.array((16,15,19),np.float32)*(1-yy)+np.array((7,7,9),np.float32)*yy
    bg=np.repeat(base,W,1)
    for y in range(40,H,64):
        for x in range(40,W,64): bg[y-1:y+2,x-1:x+2]+=9
    xx=np.linspace(-1,1,W)[None,:,None]; vig=1-0.28*(xx**2)*np.ones((H,1,1)); bg=bg*vig
    return np.ascontiguousarray(bg.astype(np.float32))
def make_bgs():
    yy=np.linspace(0,1,H)[:,None,None]; xx=np.linspace(-1,1,W)[None,:,None]
    d=np.array((16,15,19),np.float32)*(1-yy)+np.array((7,7,9),np.float32)*yy
    d=np.repeat(d,W,1)*(1-0.28*(xx**2)*np.ones((H,1,1)))
    l=np.array((247,245,243),np.float32)*(1-yy)+np.array((231,228,226),np.float32)*yy
    l=np.repeat(l,W,1)*(1-0.10*(xx**2)*np.ones((H,1,1)))
    return np.ascontiguousarray(d.astype(np.float32)),np.ascontiguousarray(l.astype(np.float32))
BGD,BGL=make_bgs()
T={'dark':True}
INK2=(52,42,44); GOLD=(205,140,10)
THEME=[0,0,1,0,1,0,1]
GRID=[(72,14,0),(64,-18,10),(96,12,12),(88,0,-22),(56,10,10),(80,-16,0),(72,0,14)]
def bg_frame(k,t):
    dark=THEME[k]; base=BGD if dark else BGL; cell,vx,vy=GRID[k]
    ys=((np.arange(H)+int(t*vy))%cell)<2; xs=((np.arange(W)+int(t*vx))%cell)<2
    m=(ys[:,None]|xs[None,:]).astype(np.float32)[...,None]
    return base+m*np.float32(8.0 if dark else -9.0)
_rn=random.Random(5); DUST=[(_rn.uniform(0,W),_rn.uniform(0,H),_rn.uniform(-14,14),_rn.uniform(-30,-9),_rn.randint(2,5),_rn.uniform(0.25,0.6)) for _ in range(30)]
def dust(fr,t,dark):
    col=(210,190,185) if dark else (156,109,106)
    for x,y,vx,vy,r,a in DUST: paste(fr,circle_spr(r,col,0),(x+vx*t)%W,(y+vy*t)%H,alpha=a*0.8)
def bl(t,off=0): return ((t+off)%4.3)<0.13
IMPACTS=[(0.12,10,0.30),(3.10,12,0.30),(B[2]+0.45,7,0.0),(B[3]+4.0,12,0.35),(B[4]+0.35,6,0.0),(B[5]+2.6,8,0.0),(B[6]+0.1,8,0.25),(B[6]+4.85,7,0.0)]
def shake_flash(t):
    sx=sy=fl=0
    for te,amp,f in IMPACTS:
        d=t-te
        if 0<=d<0.5:
            e=math.exp(-d*9); sx+=amp*e*math.sin(d*70); sy+=amp*0.6*e*math.cos(d*83); fl=max(fl,f*max(0,1-d/0.10))
    return sx,sy,fl
def camera(fr,z,tx,ty):
    M=np.array([[z,0,W/2-z*W/2+tx],[0,z,H/2-z*H/2+ty]],np.float32)
    return cv2.warpAffine(fr,M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
def speed_lines(fr,cx,cy,u,col):
    if u<=0 or u>=1: return
    r0=110+260*e_out(u); r1=r0+300*(1-u)+60
    for i in range(26):
        a=i*6.2832/26+0.1*math.sin(i*3.1)
        cv2.line(fr,(int(cx+r0*math.cos(a)),int(cy+r0*math.sin(a))),(int(cx+r1*math.cos(a)),int(cy+r1*math.sin(a))),col,max(1,int(6*(1-u))),cv2.LINE_AA)

SK={'cur':None}
def Medo(name,h):
    k=(name,h)
    if k not in SK: SK[k]=load_png(name,h)
    return SK[k]
def red_circle(fr,cx,cy,r,col=RED,alpha=1.0,glow=40):
    paste(fr,circle_spr(int(r),col,glow),cx,cy,alpha=alpha)
def ring(fr,cx,cy,r,col,width,alpha=1.0):
    key=('ring',int(r),col,width)
    if key not in SK:
        d=D(int(2*r+20),int(2*r+20)); d.circ(r+10,r+10,r,outline=col,width=width); SK[key]=d.done()
    paste(fr,SK[key],cx,cy,alpha=alpha)
def txt(fr,s,cx,cy,size,color=WHITE,rtl=True,scale=1,alpha=1,stroke=0,scolor=(0,0,0),rot=0):
    paste(fr,text_sprite(s,size,color,rtl,stroke,scolor),cx,cy,scale=scale,alpha=alpha,rot=rot)
# ---------- captions ----------
def reveal_times(words,t0,t1):
    tot=sum(len(w)+1 for w,_ in words); span=(t1-t0)*0.82; out=[]; acc=0
    for w,_ in words: out.append(t0+span*acc/tot); acc+=len(w)+1
    return out
def mk(text,t0,t1,hl=None):
    hl=hl or {}; words=[]
    for w in text.split():
        key=w.strip('،:؟.!,'); words.append((w,hl.get(key,WHITE)))
    return dict(t0=t0,t1=t1,words=words,times=reveal_times(words,t0,t1))
CAPS=[
 mk("هتدفع كام ألف جنيه في لابتوب،",0.15,2.9,{"ألف":YEL,"جنيه":YEL}),
 mk("وبعد شهر تكتشف إنه مش مناسب لاستخدامك؟",2.9,5.6,{"مش":RED,"مناسب":RED,"شهر":YEL}),
 mk("ده بيحصل مع ناس كتير،",6.26,7.74,{"ناس":YEL,"كتير":YEL}),
 mk("والسبب بسيط:",8.13,8.94,{"بسيط":EMER}),
 mk("اللي بيبيعلك بيكلمك بأرقام ومصطلحات،",9.65,12.57,{"بأرقام":YEL,"ومصطلحات":YEL}),
 mk("ومحدش بيشرحلك الكلام ده يعني إيه",12.95,15.5,{"يعني":RED,"إيه":RED}),
 mk("أهلاً بيكم،",16.24,17.1,{}),
 mk("معاكم ميدو، وعشان كده بدأنا السلسلة دي.",17.26,19.9,{"ميدو":RED}),
 mk("هنبدأ من الأول خالص:",20.6,22.0,{"الأول":YEL}),
 mk("إيه الفرق بين اللابتوب والكمبيوتر المكتبي،",22.0,25.1,{"اللابتوب":EMER,"والكمبيوتر":YEL,"المكتبي":YEL}),
 mk("وإمتى يبقى كل واحد فيهم هو الاختيار الأنسب ليك",25.1,28.45,{"الأنسب":YEL}),
 mk("وبعدها هناخد اللابتوب حتة حتة:",29.07,31.5,{"حتة":YEL}),
 mk("المعالج، الرامات، التخزين، الشاشة، كارت الشاشة، والبطارية.",31.86,37.7,{"المعالج":EMER,"الرامات":EMER,"التخزين":EMER,"الشاشة":EMER,"كارت":EMER,"والبطارية":EMER}),
 mk("كل جزء هنشرحه بالبلدي، يعني إيه وبيأثر على استخدامك إزاي.",38.3,43.3,{"بالبلدي":YEL,"استخدامك":EMER}),
 mk("وفي الآخر هتبقى قادر تختار لابتوب بنفسك،",43.9,46.5,{"قادر":EMER,"بنفسك":EMER}),
 mk("من غير ما تعتمد على كلام البائع.",46.6,48.7,{"البائع":RED}),
 mk("لو عايز تشتري لابتوب في الفترة الجاية،",49.27,51.85,{}),
 mk("أو عايز تفهم اللي في إيدك،",51.85,53.55,{}),
 mk("تابع السلسلة من أول حلقة.",53.55,55.2,{"تابع":RED,"السلسلة":YEL}),
]
@functools.lru_cache(maxsize=None)
def cap_layout(i):
    c=CAPS[i]; size=58; sp=20; maxw=970
    spr=[text_sprite(w,size,col,True,6,(0,0,0)) for w,col in c['words']]
    lines=[[]]; lw=[0]
    for k,s in enumerate(spr):
        w=s.shape[1]-12
        add=w+(sp if lines[-1] else 0)
        if lines[-1] and lw[-1]+add>maxw: lines.append([]); lw.append(0); add=w
        lines[-1].append(k); lw[-1]+=add
    lh=92; n=len(lines); pos={}
    for li,idx in enumerate(lines):
        xr=lw[li]/2; cy=(li-(n-1)/2)*lh
        for k in idx:
            w=spr[k].shape[1]-12; pos[k]=(xr-w/2,cy); xr-=w+sp
    bw=max(lw)+80; bh=n*lh+30
    return spr,pos,bw,bh
@functools.lru_cache(maxsize=None)
def plate(w,h):
    d=D(w,h); d.rrect((2,2,w-2,h-2),30,fill=(48,38,40,232),outline=RED,width=3); return d.done()
def draw_caption(fr,t,cy=1455):
    for i,c in enumerate(CAPS):
        end=c['t1']+0.28
        if i+1<len(CAPS): end=min(end,CAPS[i+1]['t0'])
        if not (c['t0']<=t<end): continue
        spr,pos,bw,bh=cap_layout(i)
        fade=min(prog(t,c['t0'],c['t0']+0.1),1-prog(t,end-0.1,end))
        paste(fr,plate(int(bw),int(bh)),540,cy,alpha=fade)
        for k,s in enumerate(spr):
            tw=c['times'][k]
            if t<tw: continue
            a=prog(t,tw,tw+0.10); sc=0.78+0.22*e_back(prog(t,tw,tw+0.22),2.4)
            x,y=pos[k]; paste(fr,s,540+x,cy+y+(1-a)*16,scale=sc,alpha=a*fade)
# ---------- shared sprites ----------
@functools.lru_cache(maxsize=None)
def term_spr(term,col=WHITE):
    ts=text_sprite(term,44,col,False); w=ts.shape[1]+52; h=84
    d=D(w,h); d.rrect((2,2,w-2,h-2),h//2,fill=(26,26,32,240),outline=RED,width=3); base=d.done()
    over(base,ts,(w-ts.shape[1])//2,(h-ts.shape[0])//2); return base
@functools.lru_cache(maxsize=None)
def card_spr(label,tag,kind,hot=False):
    w,h=440,190; d=D(w,h)
    d.rrect((2,2,w-2,h-2),30,fill=(26,26,32,245),outline=(RED if hot else (74,74,86)),width=4 if hot else 3)
    d.rrect((w-16,40,w-6,h-40),5,fill=RED)
    base=d.done(); ic=icon(kind,128)
    over(base,ic,w-34-128,(h-128)//2)
    t1=text_sprite(label,50,WHITE,True)
    if t1.shape[1]>250: t1=text_sprite(label,int(50*250/t1.shape[1]),WHITE,True)
    t2=text_sprite(tag,28,(150,150,160),False)
    cx=(w-34-128-14)//2+14
    over(base,t1,cx-t1.shape[1]//2,52-t1.shape[0]//2+30); over(base,t2,cx-t2.shape[1]//2,128+4)
    return base
@functools.lru_cache(maxsize=None)
def jbubble():
    d=D(380,100); d.rrect((2,2,378,98),40,fill=(70,70,78,230)); d.poly([(60,96),(40,140),(110,96)],fill=(70,70,78,230)) if False else None
    b=d.done(); ts=text_sprite("i7 · 16GB · RTX",38,(200,200,208),False); over(b,ts,(380-ts.shape[1])//2,(100-ts.shape[0])//2); return b
def sparkles(fr,t,cx,cy,rx,ry,n,seed,cols=(YEL,WHITE),sz=(14,26),speed=3.0):
    rnd=random.Random(seed)
    for i in range(n):
        a=rnd.uniform(0,6.28); rr=rnd.uniform(0.7,1.0); ph=rnd.uniform(0,6.28); s=rnd.randint(*sz)
        k=0.5+0.5*math.sin(t*speed+ph); paste(fr,sparkle(s,cols[i%len(cols)]),cx+rx*rr*math.cos(a),cy+ry*rr*math.sin(a),scale=0.3+0.9*k,rot=t*40+i*20,alpha=0.35+0.65*k)
# ================= SCENES =================
def scene1(fr,t):
    lt=t-B[0]; hot=prog(lt,3.0,3.25)
    pulse=1+0.02*math.sin(lt*3)
    red_circle(fr,540,1000,520*e_elastic(prog(lt,0,0.7))*pulse,RED if lt<3.1 else DRED,0.95)
    if lt>=3.1: ring(fr,540,1000,520+ (lt-3.1)*20,(255,255,255),3,alpha=max(0,0.5-(lt-3.1)*0.4))
    ring(fr,540,300,60+500*prog(lt,0.1,0.7),RED,6,alpha=0.7*(1-prog(lt,0.1,0.7))) if 0.1<lt<0.7 else None
    # price
    n=int(25000*e_out(prog(lt,0.1,1.1))); col=INK2 if lt<3.1 else RED
    sh=(math.sin(lt*70)*9 if 3.1<lt<3.6 else 0)
    scl=1+0.22*max(0,1-abs(lt-0.12)/0.25)
    txt(fr,f"{n:,} ج.م",540+sh,300,118,col,scale=scl*(1 if lt<3.1 else 0.96),alpha=prog(lt,0,0.15))
    if lt>3.1:
        wd=text_sprite(f"25,000 ج.م",118,col,True,5).shape[1]*0.96*e_out(prog(lt,3.1,3.45))
        fill_rect(fr,540+sh-wd/2,296,540+sh+wd/2,306,INK2,1.0)
        c=prog(lt,3.15,3.5); paste(fr,pill(400,92,(18,18,22),240),540,430,scale=c,alpha=c)
        txt(fr,"بعد 30 يوم",540,430,56,YEL,scale=c,alpha=c)
    # buyer
    bob=-abs(math.sin(lt*9))*20*(1-hot) if lt<3.2 else 0
    body='excited' if lt<3.2 else 'frustrated'
    gy=1385+bob
    if lt<3.2:
        sc=1.15*(1+0.025*max(0,math.sin(lt*9))); paste(fr,person((31,138,138),'excited','hold',blink=bl(lt)),540,gy,scale=sc,anchor=(0.5,1.0))
    else:
        x=540+(math.sin(lt*60)*8 if lt<3.8 else 0); k=prog(lt,3.2,3.6)
        paste(fr,person((31,138,138),'frustrated','hold'),x,1385+14*k,scale=1.15*(1-0.02*k),rot=-2.5*k,anchor=(0.5,1.0))
    # laptop in hands
    lscr='glow' if lt<3.2 else 'bad'
    lx=540+(math.sin(lt*60)*7 if 3.2<lt<3.8 else 0); ly=985+(14 if lt>=3.2 else bob)
    paste(fr,laptop(430,lscr),lx,ly)
    if lt<3.2:
        sparkles(fr,lt,540,900,330,200,9,5,(YEL,WHITE),(12,24),4)
    # bills
    for i in range(9):
        t0=0.5+i*0.33 if i<2 else 3.4+(i-2)*0.28
        if lt<t0: continue
        u=(lt-t0)/1.8
        if u>1: continue
        rnd=random.Random(i*13+1); vx=(1 if i%2 else -1)*rnd.uniform(300,470); 
        x=540+vx*u; y=1010-300*u+rnd.uniform(-30,30)-120*math.sin(u*3.1)*0; rot=rnd.uniform(-200,200)*u
        paste(fr,bill(130),x,y,rot=rot,alpha=1-prog(u,0.65,1),scale=0.9+0.2*u)
    if 3.3<lt<5.0:
        k=prog(lt,3.3,3.7); txt(fr,"- 25,000",770,1140-170*prog(lt,3.3,5.0),64,(255,255,255),rtl=False,alpha=k*(1-prog(lt,4.6,5.0)),stroke=5,scolor=(110,12,16))
def crowd_person(i):
    shirts=[(31,138,138),(244,196,48),(120,70,170),(60,120,200),(20,150,110),(210,90,60)]
    skins=[(196,138,96),(226,172,128),(170,112,76),(208,150,108),(186,126,88),(220,160,118)]
    ex=['frustrated','confused']
    return person(shirts[i%6],ex[i%2],'shrug' if i%2 else 'stand',skin=skins[i%6])
TERMS=[("i7-13700H",WHITE),("16GB DDR5",YEL),("RTX 4060",WHITE),("1TB NVMe",YEL),("144Hz",YEL),("45W TDP",WHITE),("IPS",WHITE),("Gen 4",YEL),("DDR5 4800",WHITE),("OLED",YEL),("6GB VRAM",WHITE),("2.5K",YEL)]
def scene2(fr,t):
    lt=t-B[1]
    red_circle(fr,540,960,440,(209,95,82),0.30,60)
    ck=e_back(prog(lt,0.2,0.6)); paste(fr,pill(330,88,RED),540,250,scale=ck,alpha=min(1,ck)); txt(fr,"المشكلة",540,250,52,WHITE,scale=ck)
    # crowd
    ca=1-prog(t,8.0,8.9)
    if ca>0:
        for i in range(6):
            t0=6.3+i*0.14; k=e_back(prog(t,t0,t0+0.4))
            x=150+i*156+(0 if ca==1 else -60*(1-ca)); by=1110-(1-ca)*40
            paste(fr,crowd_person(i),x,by,scale=0.5*k,anchor=(0.5,1.0),alpha=ca)
            m='؟' if i%2 else '✕'; 
            txt(fr,'؟',x,by-0.5*780-30+math.sin(t*5+i)*6,80,GOLD if i%2 else RED,scale=k,alpha=ca,stroke=4)
    # buyer
    enter=e_out(prog(t,8.0,8.9))
    bx=-200+(270+200)*enter
    ex='smile' if t<10.3 else 'confused'; pose='stand' if t<12.95 else 'shrug'
    sway=math.sin(t*4)*1.5 if t>10.3 else 0
    if enter>0: paste(fr,person((31,138,138),ex,pose,blink=bl(t,1.1)),bx,1380,scale=1.0,rot=sway,anchor=(0.5,1.0))
    # seller
    se=e_out(prog(t,8.3,9.1)); sx=1300-(1300-810)*se
    talking=9.65<=t<15.2
    sex='confident' if not talking else ('talk1' if int(t*8)%2==0 else 'talk2')
    if t>=15.2: sex='confident'
    if se>0: paste(fr,person((190,30,36),sex,'talk',skin=(226,172,128),hairstyle='slick',tie=(240,240,240),collar=(245,245,245),blink=bl(t,2.3)),sx,1380,scale=1.0,flipx=True,anchor=(0.5,1.0))
    # jargon
    mouth=(720,640)
    swirl=e_io(prog(t,12.95,13.9))
    for i,(w,c) in enumerate(TERMS):
        t0=9.7+i*0.24
        if t<t0: continue
        rnd=random.Random(i*7+3); tx=rnd.uniform(160,900); ty=rnd.uniform(430,900)
        k=prog(t,t0,t0+0.7)
        fx=lerp(mouth[0],tx,e_out(k))+math.sin(t*2+i)*18; fy=lerp(mouth[1],ty,e_out(k))+math.cos(t*2.3+i)*14
        ang=i*6.28/len(TERMS)+(t-12.95)*1.7
        ox=330+300*math.cos(ang); oy=560+170*math.sin(ang)
        x=lerp(fx,ox,swirl); y=lerp(fy,oy,swirl)
        a=e_back(prog(t,t0,t0+0.3)); fa=1-prog(t,15.2,15.7)
        if fa>0: paste(fr,term_spr(w,c),x,y,scale=min(a,1.1)*(0.9+0.1*math.sin(t*3+i)),rot=math.sin(t*3+i)*6+swirl*math.sin(t*4+i)*8,alpha=fa)
    # question marks + bubble
    if t>=11.0:
        for j,(dx,dy) in enumerate([(-120,-120),(130,-190),(-30,-250)]):
            k=e_back(prog(t,11.0+j*0.35,11.5+j*0.35)); txt(fr,'؟',bx+dx,980+dy+math.sin(t*4+j)*8-110,110,GOLD if j%2 else RED,scale=k,stroke=0)
    if t>=13.8:
        k=e_back(prog(t,13.8,14.2)); paste(fr,bubble(330,110,(255,255,255),'bc',255,INK2),270,455,scale=k,alpha=min(1,k))
        txt(fr,"يعني إيه؟",270,455,56,BLACK,scale=k)
def scene3(fr,t):
    lt=t-B[2]
    k=e_elastic(prog(lt,0,0.8))
    red_circle(fr,540,1000,500*k,RED,1.0,50)
    ring(fr,540,1000,548*k,(255,255,255),3,alpha=0.35)
    # logo slot
    e=e_elastic(prog(lt,0.7,1.5))
    paste(fr,circle_spr(105,(18,16,20),30),540,285,scale=e)
    ring(fr,540,285,105*e,RED,8); ring(fr,540,285,120*e+2*math.sin(lt*4),(255,255,255),2,alpha=0.4)
    # medo
    m=Medo('medo_wave',930); en=e_back(prog(lt,0.15,0.75),1.4)
    y=1440+(1-en)*700+math.sin(lt*3)*5
    paste(fr,m,520,y,scale=1.0,rot=math.sin(lt*7)*1.6,anchor=(0.5,1.0))
    hx,hy=520+0.30*m.shape[1],y-m.shape[0]+0.26*m.shape[0]
    for j in range(2):
        a=0.5+0.5*math.sin(lt*8+j*2.2); r=60+j*30
        d=D(260,260); d.arc((130-r,130-r,130+r,130+r),-50,50,(255,255,255,255),7); arc_spr=d.done()
        paste(fr,arc_spr,hx+86,hy+20,alpha=a*prog(lt,0.7,0.9),scale=1.0)
    sparkles(fr,lt,540,900,400,400,8,11,(WHITE,YEL),(10,20),3)
def scene4(fr,t):
    lt=t-B[3]
    red_circle(fr,540,1050,430,RED,0.92,40)
    c=e_back(prog(lt,0.2,0.65)); paste(fr,pill(420,92,RED),540,255,scale=c,alpha=min(1,c)); txt(fr,"الحلقة الأولى",540,255,52,WHITE,scale=c)
    c2=prog(lt,0.7,1.2); txt(fr,"لابتوب ولا كمبيوتر مكتبي؟",540,355-(1-c2)*20,60,INK2,alpha=c2)
    # devices
    k1=e_back(prog(lt,2.3,2.8)); k2=e_back(prog(lt,3.4,3.9)); gl=0
    hl1=prog(lt,5.0,5.3)*(1-prog(lt,6.4,6.7)); hl2=prog(lt,6.5,6.8)*(1-prog(lt,7.8,8.1))
    if hl1>0: red_circle(fr,260,560,200,EMER,0.28*hl1,60)
    if hl2>0: red_circle(fr,815,560,200,TEAL,0.35*hl2,60)
    paste(fr,laptop(400,'glow'),245,560+math.sin(lt*2)*5,scale=k1,alpha=min(1,k1))
    paste(fr,desktop(300),820,545+math.sin(lt*2+1)*5,scale=k2,alpha=min(1,k2))
    paste(fr,pill(250,70,EMER),245,745,scale=k1,alpha=min(1,k1)); txt(fr,"لابتوب",245,745,42,WHITE,scale=k1)
    paste(fr,pill(330,70,TEAL),830,745,scale=k2,alpha=min(1,k2)); txt(fr,"كمبيوتر مكتبي",830,745,42,WHITE,scale=k2)
    speed_lines(fr,535,600,prog(lt,4.0,4.6),RED if not T['dark'] else WHITE)
    if 4.0<lt<4.7: ring(fr,535,600,60+300*prog(lt,4.0,4.7),RED,6,alpha=0.8*(1-prog(lt,4.0,4.7)))
    v=e_elastic(prog(lt,4.0,4.8)); pulse=1+0.05*math.sin(lt*5)
    paste(fr,circle_spr(58,RED,20),535,600,scale=v*pulse); txt(fr,"VS",535,600,54,WHITE,rtl=False,scale=v*pulse)
    m=Medo('medo_think',650); en=e_back(prog(lt,0.3,0.9),1.3)
    paste(fr,m,540,1410+(1-en)*600+math.sin(lt*2.4)*4,anchor=(0.5,1.0),rot=math.sin(lt*1.7)*1.2)
    # thought cloud
    tc=prog(lt,4.6,5.2)
    if tc>0:
        for j,(dx,dy,r) in enumerate([(440,860,10),(395,905,16),(345,955,22)]):
            paste(fr,circle_spr(r,(255,255,255),0),dx,dy,scale=e_back(prog(lt,4.6+j*0.15,5.0+j*0.15)))
        cl=e_back(prog(lt,5.0,5.5)); paste(fr,circle_spr(80,(255,255,255),0),240,1040,scale=cl*(1+0.03*math.sin(lt*4)))
        txt(fr,"؟",240,1030,120,RED,scale=cl,stroke=0)
PARTS=[("المعالج","CPU","cpu"),("الرامات","RAM","ram"),("التخزين","STORAGE","ssd"),("الشاشة","DISPLAY","display"),("كارت الشاشة","GPU","gpu"),("البطارية","BATTERY","battery")]
SLOTS=[(780,790),(300,790),(780,990),(300,990),(780,1190),(300,1190)]
def part_times():
    c=CAPS[12]; wt=c['times']; return [wt[0],wt[1],wt[2],wt[3],wt[4],wt[6]]
PT=part_times()
def scene5(fr,t):
    lt=t-B[4]
    red_circle(fr,540,420,330,(110,16,20),0.8,60)
    L=e_elastic(prog(lt,0.2,1.0)); lift=e_io(prog(lt,1.4,2.2))
    lx,ly=540,380
    paste(fr,laptop(540,'glow'),lx,ly-0*lift,scale=L*(1-0.0))
    # connector dashes + cards
    for i,(label,tag,kind) in enumerate(PARTS):
        t0=PT[i]-0.12
        if t<t0: continue
        sx,sy=SLOTS[i]; u=prog(t,t0,t0+0.6); k=e_back(u,1.5)
        x=lerp(lx,sx,e_out(u)); y=lerp(ly+60,sy,e_out(u))
        hot=(38.3<=t<43.3) and int((t-38.3)/0.8)%6==i
        paste(fr,card_spr(label,tag,kind,hot),x,y,scale=min(1.0,0.35+0.65*k),rot=(1-u)*(-14 if i%2 else 14),alpha=min(1,u*3))
    # beat pulses
    for b in (PT[0],PT[3]):
        r=prog(t,b-0.1,b+0.7)
        if 0<r<1: ring(fr,lx,ly,300+260*r,(255,255,255),3,alpha=0.5*(1-r))
    # K chips
    chips=[(38.4,40.2,"بالبلدي",YEL,BLACK),(40.3,41.6,"يعني إيه؟",RED,WHITE),(41.7,43.4,"بيأثر على استخدامك",EMER,WHITE)]
    for a,b,s,bgc,fc in chips:
        if a<=t<b+0.15:
            k=e_back(prog(t,a,a+0.3))*(1-prog(t,b,b+0.15))
            w=int(text_sprite(s,56,fc,True).shape[1]+90)
            paste(fr,pill(w,92,bgc),540,640,scale=k,alpha=min(1,k)); txt(fr,s,540,640,56,fc,scale=k)
def scene6(fr,t):
    lt=t-B[5]
    red_circle(fr,420,1100,430,RED,0.92,40)
    for sy in (520,780):
        fill_rect(fr,70,sy,1010,sy+14,(90,90,100)); fill_rect(fr,70,sy+14,1010,sy+22,(40,40,46))
    screens=['blank','dark','glow','blank','dark','blank','glow','dark']
    pick=2
    for i in range(8):
        row=i//4; col=i%4; x=200+col*225; y=520-row*0+ (260 if row else 0)
        if i==pick and lt>1.6: continue
        paste(fr,laptop(190,screens[i]),x,y,anchor=(0.5,1.0),alpha=0.9)
    # picked laptop flight
    if lt>1.2:
        u=e_io(prog(lt,1.7,2.7)); sx,sy=200+pick*225,520
        if lt<1.7: ring(fr,sx,sy-60,130+8*math.sin(lt*12),EMER,6,alpha=0.9)
        gx=lerp(sx,165,u); gy=lerp(sy-60,1060,u); sc=lerp(1.0,1.5,u)
        paste(fr,laptop(190,'glow'),gx,gy,scale=sc,rot=(1-u)*0+math.sin(lt*3)*2*u)
    # shopper
    wk=e_out(prog(lt,0.0,1.1)); x=-180+(430+180)*wk
    step=abs(math.sin(lt*10))*10*(1-wk) if wk<1 else 0
    nchk=int(clamp((lt-3.0)/0.35,0,5))
    ex='smile' if lt<2.7 else 'confident'
    paste(fr,person((244,196,48),ex,'paper',skin=(188,128,90),pants=(40,42,52),hair=(40,28,24),blink=bl(t,0.7)),x,1385-step,anchor=(0.5,1.0),scale=0.95,rot=math.sin(lt*3)*1.2)
    pp=paper_spec(190,nchk); paste(fr,pp,x+176,1385-step-0.95*780+0.95*250,anchor=(0.5,0.9),rot=10)
    # seller far
    sk=e_back(prog(lt,2.9,3.4))
    if sk>0:
        paste(fr,person((190,30,36),'confident','stand',skin=(226,172,128),hairstyle='slick',tie=(240,240,240),collar=(245,245,245)),935,1200,scale=0.5*sk,anchor=(0.5,1.0),alpha=min(1,sk))
        ba=prog(lt,3.2,3.6)*(1-prog(lt,5.1,5.4))
        paste(fr,jbubble(),870,730,scale=0.78,alpha=ba*0.9)
        if lt>3.8:
            c=e_back(prog(lt,3.8,4.2)); paste(fr,crossmark(96),870,730,scale=c,alpha=min(1,c)*(1-prog(lt,5.1,5.4)))
    if lt>4.5:
        r=prog(lt,4.5,5.3); ring(fr,x,900,300+260*r,EMER,6,alpha=0.7*(1-r))
        sparkles(fr,lt,x,900,300,400,7,3,(EMER,YEL,WHITE),(10,20),4)
def scene7(fr,t):
    lt=t-B[6]
    k=e_elastic(prog(lt,0,0.8)); red_circle(fr,620,1000,500*k,RED,1.0,50)
    ring(fr,620,1000,545*k,WHITE,3,alpha=0.3)
    e=e_elastic(prog(lt,0.5,1.3))
    paste(fr,circle_spr(100,(18,16,20),30),540,260,scale=e); ring(fr,540,260,100*e,RED,8); ring(fr,540,260,115*e+2*math.sin(lt*4),(255,255,255),2,alpha=0.4)
    m=Medo('medo_point',1010); en=e_back(prog(lt,0.15,0.75),1.3)
    mx,my=700,1445+(1-en)*700+math.sin(lt*3)*4
    paste(fr,m,mx,my,anchor=(0.5,1.0),rot=math.sin(lt*2)*0.8)
    tipx=mx-m.shape[1]/2+0.55*m.shape[1]; tipy=my-m.shape[0]+0.41*m.shape[0]
    # laptop
    lk=e_back(prog(lt,0.6,1.2)); paste(fr,laptop(330,'glow'),255,1160+math.sin(lt*2)*5,scale=lk,rot=-4,alpha=min(1,lk))
    # button
    bk=e_back(prog(lt,1.2,1.7)); done=lt>=4.9
    press=1-0.07*max(0,1-abs(lt-4.85)/0.12)
    bx,by=tipx-290,tipy+10
    paste(fr,follow_button(520,150,False,done),bx,by,scale=0.85*bk*press,alpha=min(1,bk)) if not done else paste(fr,follow_button(520,150,False,True),bx,by,scale=0.85*press)
    # cursor tap
    if 3.6<=lt<5.6:
        u=e_io(prog(lt,3.6,4.8)); cx_=lerp(bx-340,bx-70,u); cy_=lerp(by+330,by+40,u)
        paste(fr,cursor(90),cx_,cy_,scale=1.0-0.08*max(0,1-abs(lt-4.85)/0.12),alpha=1-prog(lt,5.2,5.6),anchor=(0.1,0.08))
    if lt>4.85:
        r=prog(lt,4.85,5.6); ring(fr,bx,by,200+300*r,EMER,6,alpha=0.8*(1-r))
        sparkles(fr,lt,bx,by,300,120,9,9,(EMER,WHITE,YEL),(12,24),5)
SCENES=[scene1,scene2,scene3,scene4,scene5,scene6,scene7]
def wipe(fr,t):
    for tb in B[1:-1]:
        d=t-tb
        if -0.2<d<0.2:
            if d<0: x0=W*(1-e_io(prog(d,-0.2,0))); fill_rect(fr,x0,0,W,H,RED); fill_rect(fr,x0-14,0,x0,H,WHITE)
            else: x1=W*(1-e_io(prog(d,0,0.2))); fill_rect(fr,0,0,x1,H,RED); fill_rect(fr,x1,0,x1+14,H,WHITE)
@functools.lru_cache(maxsize=None)
def chip_spr():
    ts=text_sprite("سلسلة اختيار اللابتوب",34,WHITE,True); w=ts.shape[1]+70
    d=D(w,64); d.rrect((2,2,w-2,62),31,fill=(60,48,50,238)); b=d.done(); over(b,ts,(w-ts.shape[1])//2,(64-ts.shape[0])//2); return b
def render_frame(t):
    k=max(0,min(6,int(np.searchsorted(B,t,side='right')-1))); dark=THEME[k]; T['dark']=bool(dark)
    fr=bg_frame(k,t); dust(fr,t,dark)
    SCENES[k](fr,t)
    lt=t-B[k]; u=e_io(clamp(lt/(B[k+1]-B[k])))
    z=1+0.04*u if k%2==0 else 1.04-0.04*u
    sx,sy,fl=shake_flash(t)
    fr=camera(fr,z,14*math.sin(t*0.5+k)+sx,sy)
    if fl>0: fill_rect(fr,0,0,W,H,(255,255,255),fl)
    draw_caption(fr,t)
    paste(fr,chip_spr(),540,128,alpha=prog(t,0.05,0.4))
    fill_rect(fr,60,64,W-60,70,(255,255,255) if dark else (60,48,50),0.18); fill_rect(fr,60,64,60+(W-120)*t/B[-1],70,RED,1.0)
    wipe(fr,t)
    return np.clip(fr,0,255).astype(np.uint8)

```


## FILE: cutout.py
```python
import numpy as np, cv2
from scipy import ndimage as ndi
U='/mnt/user-data/uploads/'
def save(name, rgb, alpha):
    ys,xs=np.where(alpha>8); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    out=np.dstack([rgb,alpha])[y0:y1+1,x0:x1+1]
    cv2.imwrite(f'assets/{name}.png', cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA)); print(name,out.shape)
def white_bg(fn,name):
    im=cv2.cvtColor(cv2.imread(U+fn),cv2.COLOR_BGR2RGB); H,W=im.shape[:2]
    mx=im.max(2).astype(int); mn=im.min(2).astype(int)
    white=(mn>=225)
    gray=(mx-mn<14)&(mn>118)&(np.arange(H)[:,None]>1230)
    cand=white|gray
    lab,n=ndi.label(cand)
    border=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
    bg=np.isin(lab,list(border))
    fg=~bg
    fg=ndi.binary_fill_holes(fg)
    fg=ndi.binary_opening(fg,iterations=1)
    lab2,n2=ndi.label(fg); sizes=ndi.sum(fg,lab2,range(1,n2+1)); fg=lab2==(1+int(np.argmax(sizes)))
    a=ndi.binary_erosion(fg,iterations=1).astype(np.float32)
    a=cv2.GaussianBlur(a,(0,0),0.9)
    save(name,im,(a*255).astype(np.uint8))
def green(fn,name):
    im=cv2.cvtColor(cv2.imread(U+fn),cv2.COLOR_BGR2RGB).astype(np.float32)
    r,g,b=im[...,0],im[...,1],im[...,2]
    d=g-np.maximum(r,b)
    a=1-np.clip((d-25)/70,0,1)
    a=cv2.GaussianBlur(a,(0,0),0.7)
    # despill
    g2=np.minimum(g,np.maximum(r,b)+10); im[...,1]=np.where(d>0,g2,g)
    lab,n=ndi.label(a>0.5); sizes=ndi.sum(a>0.5,lab,range(1,n+1)); keep=lab==(1+int(np.argmax(sizes)))
    keep=ndi.binary_fill_holes(keep); a=a*ndi.binary_dilation(keep,iterations=2)
    save(name,im.astype(np.uint8),(a*255).astype(np.uint8))
white_bg('1793360684401_image.png','medo_wave')
white_bg('1793360691988_image.png','medo_think')
green('1793360699662_image.png','medo_point')

```


## FILE: sfx.py
```python
import numpy as np
from scipy.signal import butter, lfilter
SR=44100
def R(seed): return np.random.default_rng(int(seed)+11)
def tt(d): return np.arange(int(d*SR))/SR
def bp(x,lo,hi): b,a=butter(2,[lo/(SR/2),min(hi,SR/2-100)/(SR/2)],'band'); return lfilter(b,a,x)
def lp(x,f): b,a=butter(2,f/(SR/2),'low'); return lfilter(b,a,x)
def hp(x,f): b,a=butter(2,f/(SR/2),'high'); return lfilter(b,a,x)
def nrm(x): m=np.max(np.abs(x))+1e-9; return x/m
def sweep(f0,f1,d,curve=6):
    t=tt(d); f=f1+(f0-f1)*np.exp(-t*curve/d); return np.sin(2*np.pi*np.cumsum(f)/SR)
def pop(seed=0):
    r=R(seed); f0=r.uniform(500,640); t=tt(0.16); f=f0*(1+0.9*np.exp(-t*35)); x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*26)
    x[:60]+=r.normal(0,0.25,60)*np.linspace(1,0,60); return nrm(x)
def tick(seed=0):
    r=R(seed); f=r.uniform(2600,3500); t=tt(0.06); return nrm(np.sin(2*np.pi*f*t)*np.exp(-t*120)+r.normal(0,0.05,len(t))*np.exp(-t*200))
def click(seed=0):
    r=R(seed); t=tt(0.08); x=np.sin(2*np.pi*r.uniform(1500,1900)*t)*np.exp(-t*90); x[:80]+=r.normal(0,0.3,80)*np.linspace(1,0,80); return nrm(x)
def zip_(seed=0):
    r=R(seed); d=0.24; t=tt(d); x=sweep(r.uniform(260,340),r.uniform(1700,2200),d,curve=-3) if False else np.sin(2*np.pi*np.cumsum(300+1800*(t/d)**2)/SR)
    return nrm(x*np.minimum(1,t*80)*np.exp(-t*9))
def whoosh(seed=0,d=0.5):
    r=R(seed); n=r.normal(0,1,int(d*SR)); t=tt(d); env=np.sin(np.pi*np.clip(t/d,0,1))**2
    return nrm((bp(n,350,2600)*env+0.5*bp(n,1800,7000)*env**2))
def riser(seed=0,d=0.6):
    r=R(seed); n=r.normal(0,1,int(d*SR)); t=tt(d); a=(t/d)**2
    return nrm(hp(n,1500)*a*0.6+np.sin(2*np.pi*np.cumsum(180+1300*(t/d)**2)/SR)*a*0.5)
def impact(seed=0):
    r=R(seed); d=0.7; t=tt(d); f=36+60*np.exp(-t*18); sub=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*6.5)
    nz=lp(r.normal(0,1,len(t)),1100)*np.exp(-t*16)*0.7; return nrm(sub+nz)
def stomp(seed=0):
    r=R(seed); d=0.35; t=tt(d); f=50+70*np.exp(-t*30); x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*12)+lp(r.normal(0,1,len(t)),700)*np.exp(-t*30)*0.5; return nrm(x)
def sparkle(seed=0):
    r=R(seed); d=0.7; t=tt(d); x=np.zeros(len(t))
    for k,f in enumerate([2400,3100,4200,5200]):
        f*=r.uniform(0.95,1.05); s=int(k*0.04*SR); tk=t[:len(t)-s]
        x[s:]+=np.sin(2*np.pi*f*tk+0.5*np.sin(2*np.pi*9*tk))*np.exp(-tk*9)*(0.9**k)
    return nrm(x)
BANK=dict(pop=pop,tick=tick,click=click,zip=zip_,whoosh=whoosh,riser=riser,impact=impact,stomp=stomp,sparkle=sparkle)
def place(buf,sig,t,gain=1.0,pan=0.0):
    i=int(t*SR); n=min(len(sig),buf.shape[0]-i)
    if n<=0 or i<0: return
    s=sig[:n]*gain
    if isinstance(pan,tuple): p=np.linspace(pan[0],pan[1],n)
    else: p=np.full(n,pan)
    a=(p+1)*np.pi/4; buf[i:i+n,0]+=s*np.cos(a); buf[i:i+n,1]+=s*np.sin(a)

```


## FILE: mix.py
```python
import os,sys,json,subprocess,re,math
os.chdir('/home/claude/reel2'); sys.path.insert(0,'.')
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, lfilter
from sfx import *
import scenes
B=scenes.B; PT=scenes.PT; TOTAL=B[-1]
N=int((TOTAL+0.3)*SR)
# ---- voice ----
sr,v=wavfile.read('out/vo24.wav'); v=v.astype(np.float32)/32768
if v.ndim>1: v=v.mean(1)
v=resample_poly(v,441,240).astype(np.float32)
vo=np.zeros(N,np.float32); vo[:min(N,len(v))]=v[:N]
vpk=np.max(np.abs(vo)); print('vo peak',vpk)
# ---- events ----
E=[]
def ev(t,name,g=1.0,seed=0,pan=0.0): E.append((t,name,g,seed,pan))
ev(0.12,'impact',1.0); ev(0.12,'pop',0.7)
for i in range(14): ev(0.10+i*0.07,'tick',0.35,i)
ev(0.45,'sparkle',0.5,1); ev(0.6,'whoosh',0.3,2,(-.5,.6))
ev(2.55,'riser',0.8); ev(3.10,'impact',1.0,3); ev(3.12,'stomp',0.6); ev(3.15,'pop',0.6,2); ev(3.3,'pop',0.5,3)
for i in range(7): ev(3.4+i*0.28,'whoosh',0.28,10+i,(-.7,.7) if i%2 else (.7,-.7))
for i in range(1,7): ev(B[i]-0.19,'whoosh',0.9,40+i,(0.8,-0.8))
for i in range(6): ev(6.3+i*0.14,'pop',0.55,i,(-0.7+0.28*i))
ev(B[1]+0.2,'pop',0.7,5)
ev(8.0,'whoosh',0.5,7,(-.8,0)); ev(8.3,'whoosh',0.5,8,(.8,0))
for i in range(12): ev(9.7+i*0.24,'pop',0.35,20+i,(-.7+0.13*i)); 
for j in range(3): ev(11.0+j*0.35,'pop',0.5,30+j,0.0)
ev(12.95,'whoosh',0.6,9,(-.6,.6)); ev(13.8,'pop',0.8,4)
b=B[2]; ev(b+0.15,'whoosh',0.5,1,(.8,-.2)); ev(b-0.1,'riser',0.6); ev(b+0.45,'impact',0.8,2); ev(b+0.7,'sparkle',0.6,2); ev(b+1.3,'pop',0.8,3)
for i in range(4): ev(b+1.8+i*0.55,'tick',0.25,i)
b=B[3]; ev(b+0.3,'pop',0.7,1); ev(b+0.8,'pop',0.5,2); ev(b+0.3,'whoosh',0.4,3,(.8,0))
ev(b+2.4,'pop',0.8,4); ev(b+2.35,'zip',0.4,1); ev(b+3.5,'pop',0.8,5); ev(b+3.45,'zip',0.4,2)
ev(b+3.4,'riser',0.8); ev(b+4.0,'impact',1.0,6); ev(b+4.02,'sparkle',0.7,3)
for i in range(3): ev(b+4.6+i*0.15,'pop',0.35,10+i)
ev(b+5.0,'pop',0.7,7); ev(b+5.0,'tick',0.5,1); ev(b+6.5,'tick',0.5,2)
b=B[4]; ev(b+0.4,'pop',0.8,1); ev(b+0.5,'impact',0.5,4); ev(b+0.55,'sparkle',0.4,4)
for i in range(6):
    p=-0.5 if i%2==0 else 0.5
    ev(PT[i]-0.12,'zip',0.5,i,(0,p)); ev(PT[i]+0.45,'pop',0.55,i,p); ev(PT[i]+0.5,'tick',0.4,i)
ev(PT[0],'sparkle',0.4,5); ev(PT[3],'sparkle',0.4,6)
for i in range(6): ev(38.3+i*0.8,'tick',0.45,i)
for t in (38.4,40.3,41.7): ev(t,'pop',0.8,int(t))
b=B[5]; ev(b+0.05,'whoosh',0.4,2,(-.9,0)); ev(b+1.2,'sparkle',0.5,7); ev(b+1.7,'zip',0.5,3); ev(b+2.6,'impact',0.6,5); ev(b+2.7,'pop',0.8,6)
ev(b+2.95,'pop',0.7,7,(.6)); ev(b+3.2,'pop',0.5,8,(.6)); ev(b+3.8,'stomp',0.8,9,(.5))
for i in range(5): ev(b+3.0+i*0.35,'tick',0.5,i,-0.2)
ev(b+4.5,'sparkle',0.6,8)
b=B[6]; ev(b+0.1,'impact',0.9,7); ev(b+0.2,'whoosh',0.4,3,(.8,0)); ev(b+0.6,'pop',0.7,9); ev(b+0.7,'pop',0.6,10,-.5); ev(b+1.3,'pop',0.8,11,-.3)
ev(b+3.6,'whoosh',0.35,5,(-.8,-.2)); ev(b+4.85,'click',1.0,1,-.3); ev(b+4.88,'pop',0.7,12,-.3); ev(b+4.9,'sparkle',0.8,9,-.3)
sf=np.zeros((N,2),np.float32); cache={}
for t,name,g,seed,pan in E:
    k=(name,seed)
    if k not in cache: cache[k]=BANK[name](seed).astype(np.float32)
    place(sf,cache[k],t,g*0.40*vpk,pan)
# ---- music bed ----
bpm=76; beat=60/bpm; m=np.zeros(N,np.float32); tm=np.arange(N)/SR
chords=[(110,130.8,164.8,220),(87.3,110,130.8,174.6),(130.8,164.8,196,261.6),(98,123.5,146.8,196)]
nb=int(TOTAL/(beat*4))+2; r=np.random.default_rng(3)
for c in range(nb):
    t0=c*beat*4; ch=chords[c%4]; L=beat*4*1.12; i0=int(t0*SR); n=min(int(L*SR),N-i0)
    if n<=0: break
    t=np.arange(n)/SR; w=np.sin(np.pi*np.clip(t/L,0,1))**1.5
    pad=sum(np.sin(2*np.pi*f*t)+0.4*np.sin(2*np.pi*f*2*t*1.002)+0.25*np.sin(2*np.pi*f*3*t) for f in ch)/len(ch)
    m[i0:i0+n]+=pad*w*0.42
    for bt in (0,2):  # bass + kick
        j=int((t0+bt*beat)*SR); nn=min(int(0.7*SR),N-j)
        if nn>0:
            tb=np.arange(nn)/SR; m[j:j+nn]+=np.sin(2*np.pi*(ch[0]/2)*tb)*np.exp(-tb*4)*0.5
            kf=45+70*np.exp(-tb*40); m[j:j+nn]+=np.sin(2*np.pi*np.cumsum(kf)/SR)*np.exp(-tb*14)*0.45
    for s8 in range(8):  # pluck arpeggio + hats
        j=int((t0+s8*beat/2)*SR); nn=min(int(0.35*SR),N-j)
        if nn<=0: continue
        tb=np.arange(nn)/SR
        if r.random()<0.65:
            f=ch[r.integers(0,4)]*2*(2 if r.random()<0.3 else 1); m[j:j+nn]+=(np.sin(2*np.pi*f*tb)+0.3*np.sin(2*np.pi*2*f*tb))*np.exp(-tb*9)*0.16
        if s8%2==1:
            h=hp(r.normal(0,1,nn),7000)*np.exp(-tb*70); m[j:j+nn]+=h*0.10
b2,a2=butter(2,4800/(SR/2),'low'); m=lfilter(b2,a2,m).astype(np.float32); m/=np.max(np.abs(m))
# duck under VO
env=np.abs(vo); bb,aa=butter(1,6/(SR/2),'low'); env=lfilter(bb,aa,env)/ (vpk*0.35+1e-9); duck=1-0.62*np.clip(env,0,1)
m=m*duck
fade=np.clip((TOTAL+0.3-tm)/1.2,0,1)*np.clip(tm/0.8,0,1)
mus=np.stack([m*fade,m*fade],1)*0.17*vpk*1.6
mix=np.stack([vo,vo],1)+sf+mus
mix=np.clip(mix/ max(1.0,np.max(np.abs(mix))*1.02),-1,1)
wavfile.write('out/mix_raw.wav',SR,(mix*32767).astype(np.int16))
# ---- two-pass loudnorm ----
p1=subprocess.run(['ffmpeg','-hide_banner','-i','out/mix_raw.wav','-af','loudnorm=I=-14.5:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
j=json.loads(p1[p1.rindex('{'):p1.rindex('}')+1]); print({k:j[k] for k in ('input_i','input_tp','input_lra','input_thresh','target_offset')})
af=f"loudnorm=I=-14.5:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','out/mix_raw.wav','-af',af,'-ar','44100','out/final_audio.wav'],check=True)
p3=subprocess.run(['ffmpeg','-hide_banner','-i','out/final_audio.wav','-af','loudnorm=I=-14.5:TP=-1.5:print_format=summary','-f','null','-'],capture_output=True,text=True).stderr
print([l for l in p3.splitlines() if 'Input Integrated' in l or 'Input True Peak' in l])

```


## FILE: chunk.py
```python
import os,sys,subprocess
os.chdir('/home/claude/reel2'); sys.path.insert(0,'.')
from scenes import *
a,b=int(sys.argv[1]),int(sys.argv[2]); out=f'out/c_{a:05d}.mp4'
if os.path.exists(out): sys.exit()
cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',out+'.tmp.mp4']
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for i in range(a,b): p.stdin.write(render_frame(i/30).tobytes())
p.stdin.close(); p.wait(); os.rename(out+'.tmp.mp4',out); print('chunk',a,b,flush=True)

```


## FILE: run_all.sh
```bash
#!/bin/sh
cd /home/claude/reel2
for a in 0 276 552 828 1104 1380; do
  b=$((a+276)); [ $b -gt 1656 ] && b=1656
  python3 chunk.py $a $b >> out_log.txt 2>&1
done
ls out/c_0*.mp4 out/c_1*.mp4 | grep -v tmp | sed "s#^#file '/home/claude/reel2/#; s#\$#'#" > out/list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i out/list.txt -c copy out/video_only.mp4 >> out_log.txt 2>&1
echo VIDEODONE >> out_log.txt

```
