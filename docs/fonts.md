# الخطوط — Type system

**١٢٥ عيلة خط (٦١ عربي + ٦٤ إنجليزي)، كلها مجانية:** ١٢٣ عيلة SIL OFL 1.1 + **Permanent Marker**
(Apache-2.0، Font Diner) + **Ubuntu** (Ubuntu Font Licence 1.0، Canonical) — استخدام تجاري، إعادة توزيع، ومن غير أي إتاوة على الشاشة. مفيش خط مدفوع ولا
خط محتاج ترخيص منفصل — ودي ميزة مش تفصيلة: أي ريل بيطلع من هنا يقدر يتسلّم لعميل أو يتنشر مدفوع من غير
سؤال. التفاصيل لكل عيلة في `assets/fonts/fonts.json`، والفهرس الكامل في آخر الملف ده.

`assets/fonts/fonts.json` هو المصدر الوحيد لقائمة الخطوط والأدوار؛ P/K/R بيقروا منه مباشرة:
`lib.font(size, family, weight)` في P، `lib/fonts.js` في K، و`@font-face` مولّد من الـmanifest في R.
كل عيلة معاها حقل `status`: `ok` (عدّت حاجز التشكيل) أو `review` (مقاسة ≥ 0.20 — انظر قسم «الحوض»).

## المختصرة للنماذج الضعيفة | Curated shortlist

الموديل الضعيف بيتوه مع ١٢٥ اختيار. `medo-motion/looks/shortlist.json` فيه **8 عربي + 5 لاتيني**
مختارين لأدوار محددة (display ثقيل للهوك، جيوماتري للعناوين والأرقام، Plex للبيانات التقنية، Almarai
للنصوص الصغيرة...) — كلهم `status: "ok"` ومقاسين. القاعدة والمبرر في `medo-motion/looks/README.md`:

- **موديل ضعيف:** يختار من المختصرة فقط؛ غير كده يحتاج مبرر مكتوب في `plan/text-direction.json`.
- **موديل قوي:** حر في أي `ok` بمبرر؛ `review` للقوام النسجي عمدًا فقط، أبدًا للنص القابل للقراءة.
- الـLooks المقفولة اتسجلت في `medo-motion/looks/looks.json` (٦ تركيبات: house, tech-dark,
  explain-paper, kinetic-hook, swiss-data, warm-story) — ستايل + زوج خطوط + تقنيات + انتقال +
  خلفية + موسيقى، من غير باليت (الهوية في `brand/brand.json`).

## مفيش خط افتراضي مفروض | No forced default

**الوكيل هو اللي بيختار الخط الأكثر جاذبية ومناسبة للريل** — عربي أو إنجليزي — لكل مشهد/عنصر،
وبيسجّل اختياره في `plan/text-direction.json` (`fontStyles` لكل دور + `fontElements` لأي عنصر
محتاج خط خاص) مع تبرير قصير. Cairo وInter مجرد **شبكة أمان** لكروم النظام (preview/progress)،
مش قرار إبداعي مفروض. اللينت T05 وبوابات الرندر بيرفضوا أي نص من غير خط مختار صريح.

قواعد إبداعية: اختار **زوج** عربي/لاتيني بنفس الإحساس، وحافظ على تشكيل الكلمة كاملة،
ويفضّل ما تزيدش عن عيلتين في المشهد إلا لسبب متسجّل.

### عربي | Arabic

*العائلات الأساسية الموثقة (الباقي في الفهرس الكامل آخر الملف + `shortlist.json` للمختصرة):*

| العيلة | الأوزان | دورها | بتتقرن بـ |
|---|---|---|---|
| **Cairo** | 400/700/800/900 | اختيار متاح + شبكة أمان لكروم النظام (مش default مفروض) | Inter |
| **Tajawal** | 400/500/700/800 | عنوان هندسي قصير + أرقام (سطر واحد واثق) | Space Grotesk |
| **Alexandria** | 700/800 | عنوان تقيل عريض — كلمة الهوك، رقم كبير | Anton |
| **Kufam** | 500/700 | كوفي هندسي — كارت فصل، فريم بوستر، رقم ضخم | Space Grotesk |
| **El Messiri** | 500/700 | ديسبلاي بلمسة مصرية — عنوان دافي مش كوربوريت | Inter |
| **IBM Plex Sans Arabic** | 400/600 | تقني/UI — صفوف بيانات، شاشة جهاز، ليبل وجنبه رقم | IBM Plex Mono |
| **Almarai** | 400/700 | كابشن صغير ونص طويل — الوضوح أهم من الشخصية | Inter |
| **Amiri** | 400/700 | نسخ (سيريف) — اقتباس، جملة جدية، إحساس تحريري | Instrument Serif |
| **Rubik** | 400/500/700/800/900 | عربي+لاتيني مدوّر حديث — هوك ودّي، كابشن سوشيال، أرقام تقيلة | Sora |
| **Changa** | 400/600/700/800 | عربي مضغوط — عناوين قوية، تايب حركي ضيق، عدّادات | Archivo Black |
| **Readex Pro** | 400/600/700 | عربي+لاتيني معاصر نضيف — body/UI واضح بلمسة حديثة | Sora |
| **Lalezar** | 400 | ديسبلاي تقيل — فريم بوستر، كارت فصل، كلمة عربية ضخمة | Bebas Neue |

### إنجليزي | Latin

*العائلات الأساسية الموثقة (الباقي في الفهرس الكامل آخر الملف + `shortlist.json` للمختصرة):*

| العيلة | الأوزان | دورها | بتتقرن بـ |
|---|---|---|---|
| **Inter** | 400/600/800 | اختيار متاح للاتيني + شبكة أمان للسطور المخلوطة | Cairo |
| **Space Grotesk** | 500/700 | ديسبلاي تقني — أسماء منتجات، هيدر بإحساس هندسي | Alexandria |
| **IBM Plex Sans** | 400/600 | النص اللاتيني في عيلة Plex — بتقعد جنب العربية ١:١ | IBM Plex Sans Arabic |
| **IBM Plex Mono** | 400/600 | كود، مواصفات، أرقام لازم تتراص — لوك تيرمنال/تيليمتري | IBM Plex Sans Arabic |
| **Anton** | 400 | وزن واحد تقيل — هوك، رقم واحد ضخم، CTA | Kufam |
| **Instrument Serif** | 400 | سيريف تحريري — اقتباس على خلفية سانس | Amiri |
| **Archivo Black** | 400 | جروتيسك تقيل — هوك صاخب، رقم واحد ضخم، CTA ختم | Changa |
| **Bebas Neue** | 400 | كاب طويل مضغوط — عناوين تريلر، عدّادات، ليبل حركي | Noto Kufi Arabic |
| **Sora** | 400/700/800 | لاتيني هندسي حديث — هيدر منتج/UI جنب العربي المدوّر | Rubik |

## أزواج جاهزة | Pairings

اختر **زوج** مش خط: العربي والإنجليزي لازم يكون عندهم نفس الإحساس في الطول والوزن.

1. `Cairo` + `Inter` — شبكة أمان محايدة (مش اختيار مفروض).
2. `Tajawal` + `Space Grotesk` — تقني حديث، منتجات/أدوات.
3. `Alexandria` + `Anton` — هوك صارخ، رقم كبير، ترند.
4. `Kufam` + `Space Grotesk` — بوستري/فصلي، أقوى شخصية.
5. `El Messiri` + `Inter` — دافي مصري، محتوى شخصي.
6. `IBM Plex Sans Arabic` + `IBM Plex Mono` — سوبر-فاميلي: أرقام ومواصفات وتيليمتري.
7. `Amiri` + `Instrument Serif` — اقتباس/جملة جدية (نادر، لمشهد واحد).
8. `Rubik` + `Sora` — سوشيال ودّي حديث، هوك وكابشن مدوّر.
9. `Changa` + `Archivo Black` — إمباكت مضغوط، عناوين قوية وعدّادات.
10. `Lalezar` + `Bebas Neue` — بوستر/تريلر، كلمة عربية ضخمة + كاب لاتيني.
11. `Readex Pro` + `Sora` — UI/body معاصر نضيف.

## الاستخدام | Usage

```python
# engine P — lib.font(size, family=None, weight=800)
big  = lib.font(120, 'Alexandria')            # أقرب وزن ≤ 800
body = lib.font(58, 'Readex Pro', 600)        # اختيار الوكيل، مش default
mono = lib.font(34, 'IBM Plex Mono', 600)
sprite = lib.text_sprite('السرعة', 96, lib.WHITE, family='Kufam')
```
```js
// engine K — lib/fonts.js (بيقرا assets/fonts/fonts.json)
import { useFont, family } from '../lib/fonts.js';
export async function init() { await useFont('Kufam', 700); }
ctx.font = `700 120px ${family('Kufam')}`;      // '"Kufam", "Cairo", sans-serif'
```
محرك R بيحمّل كل عائلات الـmanifest محليًا من `public/fonts/<Family>/` وقت إنشاء المشروع، وبيولّد `@font-face` من `fonts.json` — من غير Google Fonts أو اتصال إنترنت أثناء الرندر. `DirectedText` بيطبّق الخط اللي الوكيل اختاره في الخطة.

- **الوزن مش العيلة**: قبل ما تغيّر العيلة، جرّب ترفع الوزن أو تقلّله — أغلب المشاكل بتتحل كده.
- **ممنوع letter-spacing على العربي** (بيقصف الحروف) — `reference/arabic-typography.md`.
- **ممنوع خط مش في المانيفست** على الشاشة. لو محتاج عيلة جديدة، ضيفها بـ`tools/fonts_install.py`.

## المعاينة | See them

```bash
python3 tools/fonts_install.py     # تحميل/تحديث (npm: @expo-google-fonts/*، TTF + OFL)
make fonts                         # نفس الحاجة
python3 tools/fonts_preview.py     # cache/fonts-sheet.png — العيلات + الأزواج على خلفية البراند
python3 tools/fonts_preview.py --light   # نفس الشيت على الورق
```
الشيت بيرسم بـ`arabic_shape` (HarfBuzz) — يعني اللي بتشوفه هو اللي المحرك P بيرسمه بالظبط.

## إضافة عيلة | Adding one

1. ضيف سطر في `FAMILIES` جوه `tools/fonts_install.py`: `family`, `npm` (اسم الحزمة تحت
   `@expo-google-fonts/`), `weights`, `role`, `pairs`, `tags`.
2. `python3 tools/fonts_install.py --only "الاسم"` → بينزّل الـTTF و`OFL.txt` ويحدّث المانيفست.
3. `python3 tools/fonts_preview.py` وشوفها بعينك قبل ما تستخدمها في شغل حقيقي.
4. ضيفها للجدول فوق — `tests/test_fonts.py` بيفشل لو عيلة في المانيفست مش مذكورة هنا.

## الحوض (Quarantine) | Tested and measured

كل عائلة عربية اتقاست على كلمة «النهاردة» @ 54px بكل أوزانها المتاحة (HarfBuzz + FreeType، 2026-11-09).
العائلات اللي نسبة تراكب outline/advance فيها **≥ 0.20** علّمناها `status: "review"` في المانيفست —
يعني: الخط **مش فاسد**، بس مش مناسب كنقطة بداية أو للنص الطويل (العرض الحوّالي/النسخي المتصل بطبيعته
بيتداخل). موجودة في المانيفست وتقدر تستخدمها عمدًا للقوام النسجي، مش جزء من المختصرة:

| العائلة | أسوأ نسبة مقاسة | ملاحظة |
|---|---|---|
| Jomhuria | 0.495 | ديسبلاي نسخي ثقيل |
| Aref Ruqaa | 0.421 | رقعة متصلة (الأصلي مش Ink) |
| Noto Nastaliq Urdu | 0.371 | نستعليق — التداخل جزء من الأسلوب |
| Aref Ruqaa Ink | 0.342 | رقعة Ink للبورتريه |
| Gulzar | 0.317 | |
| Noto Sans Arabic | 0.272 | variable default — راجع إنستانس مختلف لو احتجته |
| Estedad | 0.247 | variable default |
| Reem Kufi | 0.247 | variable default |
| Reem Kufi Fun | 0.247 | variable default |
| Mirza | 0.246 | كل الأوزان المشحونة ≥ 0.21 |
| Reem Kufi Ink | 0.241 | |
| Noto Naskh Arabic | 0.231 | variable default |
| Noto Kufi Arabic | 0.223 | variable default |
| Katibeh | 0.214 | |
| Fustat | 0.207 | variable default |

أي عيلة من دول تعدّي الحاجز بعد تحديث الخط: اقلبها `ok` في المانيفست + حدّث الملف ده — اختبار
`tests/test_fonts.py::test_arabic_families_shape_without_collisions` بيفشل في الاتجاهين.

- **خطوط بترخيص مش OFL** — ممنوعة إلا **Permanent Marker** (Apache-2.0) و**Ubuntu** (UFL-1.0)،
  المسجّلتين وقت التدقيق بملفاتها وترخيصها المعلن في المانيفست.
- **الخطوط متغيّرة (variable)** — المانيفست بيشحن الـdefault instance؛ القياس عليها هو المعتمد،
  ومفيش instancing خطوات إضافية في الرندر.

## الترخيص | Licence

١٢٣ عيلة معاها `OFL.txt` في فولدرها (`assets/fonts/<Family>/OFL.txt`)، و**Permanent Marker** معاها
`LICENSE.txt` (Apache-2.0 — Font Diner, 2010)، و**Ubuntu** معاها `UFL.txt` (Ubuntu Font Licence 1.0 —
Canonical, 2011). الكل مسجّل في `assets/CREDITS.md`. التراخيص بتسمح
بالاستخدام التجاري والتعديل وإعادة التوزيع؛ لو عدّلت ملف خط، لازم تغيّر اسمه (شرط في الرخصة) — إحنا
مش بنعدّل، بنستخدم زي ما هو. المانيفست بيسجّل الترخيص المعلن لكل عيلة واختبار
`test_every_family_carries_its_licence` بيفحصه.

## التحقق ومصدر التنزيل المقفول

`python3 tools/fonts_install.py --check` فحص read-only لكل عائلة في المانيفست (مش الـ21 الأولى بس): كل وزن، كل ملف ترخيص معلن، وحقلي الترخيص والـ`status`.
القائمة المتوقعة في `FAMILIES` هي نفس اللي بيستخدمها doctor وsetup، مش حد أدنى ثابت للعدد.
التنزيل بيستخدم إصدارات npm وSHA-512 في `tools/font-packages.lock.json`؛ أي checksum مختلف بيوقف التثبيت.
**تغطية القفل (تحديث 2026-11-09):** `tools/font-packages.lock.json` بقى مثبّت **١٢١ حزمة npm** —
الـ21 الأصلية المدارة عبر `pack()`، و**+ ١٠٠ عائلة Alansari** اتضافت في 2026-11-09 من سجل npm مباشرة
(`dist.integrity` لكل حزمة، اتحققنا باستيفاء ٤ عيّنات عشوائيًا بتنزيل الحزمة ومقارنة SHA-512 بالسجل).
**الاستثناءات الأربع** (مفيش ليها حزمة `@expo-google-fonts` — متغيرة الخط ومتاحة عبر Google Fonts specimens فقط؛ HTTP 404 على السجل بتاريخ 2026-11-09): **Firjar**، **Thabit**،
**Noto Naskh Arabic UI**، **Noto Sans Arabic UI** — كلهم OFL-1.1، ملفات الترخيص والخطوط على القرص،
ومصدرهم معلن في `fonts.json` (`source`). الفحص المقروء فقط: `python3 tools/fonts_install.py --verify-lock`
(بيطابق القفل ↔ المانيفست ↔ ملفات الترخيص على القرص) و`tests/test_fonts_lock.py`.
تجديد القفل قرار مقصود: لازم بعده مراجعة OFL وتشغيل اختبارات الخطوط والرندر؛ تحديثه لوحده **مش بيغير الملفات المضمّنة**.

## الفهرس الكامل — الـ125 عيلة | Full index

كل العائلات الموجودة في `assets/fonts/fonts.json` (مولّدة منه 2026-11-09): العائلات الأساسية الموثقة فوق،
والـ`additional option` هنا بنفس الترخيص وتعدّت نفس بوابة التشكيل إلا لو معلّمة `review`.

| العائلة | السكريبت | الدور | تقترن بـ | الحالة |
|---|---|---|---|---|
| Alan Sans | arabic | additional option | Cairo | ok |
| Alexandria | arabic | big display Arabic (hook word, key number) | Space Grotesk | ok |
| Alkalami | arabic | additional option | Cairo | ok |
| Almarai | arabic | small captions and long body where legibility beats per… | Inter | ok |
| Alyamama | arabic | additional option | Cairo | ok |
| Amiri | arabic | naskh serif | Instrument Serif | ok |
| Amiri Quran | arabic | additional option | Cairo | ok |
| Aref Ruqaa | arabic | additional option | Cairo | review |
| Aref Ruqaa Ink | arabic | additional option | Cairo | review |
| Badeen Display | arabic | additional option | Cairo | ok |
| Baloo Bhaijaan 2 | arabic | additional option | Cairo | ok |
| Beiruti | arabic | additional option | Cairo | ok |
| Blaka | arabic | additional option | Cairo | ok |
| Blaka Hollow | arabic | additional option | Cairo | ok |
| Blaka Ink | arabic | additional option | Cairo | ok |
| Cairo | arabic | available option / system-chrome fallback | Inter | ok |
| Cairo Play | arabic | additional option | Cairo | ok |
| Cascadia Code | arabic | additional option | Cairo | ok |
| Cascadia Mono | arabic | additional option | Cairo | ok |
| Changa | arabic | condensed Arabic display | Archivo Black | ok |
| El Messiri | arabic | Egyptian-flavoured modern display | Inter | ok |
| Estedad | arabic | additional option | Cairo | review |
| Firjar | arabic | additional option | Cairo | ok |
| Fustat | arabic | additional option | Cairo | review |
| Gulzar | arabic | additional option | Cairo | review |
| Handjet | arabic | additional option | Cairo | ok |
| Harmattan | arabic | additional option | Cairo | ok |
| IBM Plex Sans Arabic | arabic | technical / UI / telemetry | IBM Plex Mono | ok |
| Jomhuria | arabic | additional option | Cairo | review |
| Katibeh | arabic | additional option | Cairo | review |
| Kufam | arabic | kufic-geometric statement | Anton | ok |
| Lalezar | arabic | bold display statement | Bebas Neue | ok |
| Lateef | arabic | additional option | Cairo | ok |
| Lemonada | arabic | additional option | Cairo | ok |
| Mada | arabic | additional option | Cairo | ok |
| Marhey | arabic | additional option | Cairo | ok |
| Markazi Text | arabic | additional option | Cairo | ok |
| Mirza | arabic | additional option | Cairo | review |
| Noto Kufi Arabic | arabic | additional option | Cairo | review |
| Noto Naskh Arabic | arabic | additional option | Cairo | review |
| Noto Naskh Arabic UI | arabic | additional option | Cairo | ok |
| Noto Nastaliq Urdu | arabic | additional option | Cairo | review |
| Noto Sans Arabic | arabic | additional option | Cairo | review |
| Noto Sans Arabic UI | arabic | additional option | Cairo | ok |
| Oi | arabic | additional option | Cairo | ok |
| Parastoo | arabic | additional option | Cairo | ok |
| Playpen Sans Arabic | arabic | additional option | Cairo | ok |
| Qahiri | arabic | additional option | Cairo | ok |
| Rakkas | arabic | additional option | Cairo | ok |
| Readex Pro | arabic | clean contemporary Arabic+Latin | Sora | ok |
| Reem Kufi | arabic | additional option | Cairo | review |
| Reem Kufi Fun | arabic | additional option | Cairo | review |
| Reem Kufi Ink | arabic | additional option | Cairo | review |
| Rubik | arabic | rounded modern Arabic+Latin | Sora | ok |
| Ruwudu | arabic | additional option | Cairo | ok |
| Scheherazade New | arabic | additional option | Cairo | ok |
| Tajawal | arabic | geometric headlines and numbers | Inter | ok |
| Thabit | arabic | additional option | Cairo | ok |
| Vazirmatn | arabic | additional option | Cairo | ok |
| Vibes | arabic | additional option | Cairo | ok |
| Zain | arabic | additional option | Cairo | ok |
| Abril Fatface | latin | additional option | Inter | ok |
| Anton | latin | one heavy display weight | Reem Kufi | ok |
| Archivo | latin | additional option | Inter | ok |
| Archivo Black | latin | heavy grotesque | Changa | ok |
| Audiowide | latin | additional option | Inter | ok |
| Bangers | latin | additional option | Inter | ok |
| Barlow | latin | additional option | Inter | ok |
| Barlow Condensed | latin | additional option | Inter | ok |
| Bebas Neue | latin | tall condensed caps | Noto Kufi Arabic | ok |
| Bricolage Grotesque | latin | additional option | Inter | ok |
| Caveat | latin | additional option | Inter | ok |
| Chakra Petch | latin | additional option | Inter | ok |
| Chivo | latin | additional option | Inter | ok |
| Cormorant Garamond | latin | additional option | Inter | ok |
| Dancing Script | latin | additional option | Inter | ok |
| DM Sans | latin | additional option | Inter | ok |
| DM Serif Display | latin | additional option | Inter | ok |
| Exo 2 | latin | additional option | Inter | ok |
| Fira Code | latin | additional option | Inter | ok |
| Fira Sans | latin | additional option | Inter | ok |
| Fraunces | latin | additional option | Inter | ok |
| IBM Plex Mono | latin | code, specs, numbers that must line up | IBM Plex Sans Arabic | ok |
| IBM Plex Sans | latin | Latin half of the Plex superfamily | IBM Plex Sans Arabic | ok |
| IBM Plex Serif | latin | additional option | Inter | ok |
| Instrument Serif | latin | editorial serif | Amiri | ok |
| Inter | latin | available option / system-chrome fallback | Cairo | ok |
| JetBrains Mono | latin | additional option | Inter | ok |
| Josefin Sans | latin | additional option | Inter | ok |
| Jost | latin | additional option | Inter | ok |
| Lexend | latin | additional option | Inter | ok |
| Libre Baskerville | latin | additional option | Inter | ok |
| Lobster | latin | additional option | Inter | ok |
| Lora | latin | additional option | Inter | ok |
| Manrope | latin | additional option | Inter | ok |
| Merriweather | latin | additional option | Inter | ok |
| Michroma | latin | additional option | Inter | ok |
| Monoton | latin | additional option | Inter | ok |
| Montserrat | latin | additional option | Inter | ok |
| Nunito | latin | additional option | Inter | ok |
| Open Sans | latin | additional option | Inter | ok |
| Orbitron | latin | additional option | Inter | ok |
| Oswald | latin | additional option | Inter | ok |
| Outfit | latin | additional option | Inter | ok |
| Pacifico | latin | additional option | Inter | ok |
| Permanent Marker | latin | additional option | Inter | ok |
| Playfair Display | latin | additional option | Inter | ok |
| Plus Jakarta Sans | latin | additional option | Inter | ok |
| Poppins | latin | additional option | Inter | ok |
| Quicksand | latin | additional option | Inter | ok |
| Rajdhani | latin | additional option | Inter | ok |
| Raleway | latin | additional option | Inter | ok |
| Righteous | latin | additional option | Inter | ok |
| Roboto | latin | additional option | Inter | ok |
| Russo One | latin | additional option | Inter | ok |
| Sora | latin | geometric modern Latin | Rubik | ok |
| Source Sans 3 | latin | additional option | Inter | ok |
| Space Grotesk | latin | technical display | Alexandria | ok |
| Space Mono | latin | additional option | Inter | ok |
| Syne | latin | additional option | Inter | ok |
| Tektur | latin | additional option | Inter | ok |
| Ubuntu | latin | additional option | Inter | ok |
| Unbounded | latin | additional option | Inter | ok |
| Urbanist | latin | additional option | Inter | ok |
| Work Sans | latin | additional option | Inter | ok |