# الخطوط — Type system

**٢١ عيلة خط، كلها مجانية (SIL OFL 1.1):** استخدام تجاري، إعادة توزيع، ومن غير أي إتاوة أو حقوق على
الشاشة. مفيش خط مدفوع ولا خط محتاج ترخيص منفصل — ودي ميزة مش تفصيلة: أي ريل بيطلع من هنا يقدر يتسلّم
لعميل أو يتنشر مدفوع من غير سؤال.

`assets/fonts/fonts.json` هو المصدر الوحيد لقائمة الخطوط والأدوار؛ P/K/R بيقروا منه مباشرة:
`lib.font(size, family, weight)` في P، `lib/fonts.js` في K، و`@font-face` مولّد من الـmanifest في R.

## مفيش خط افتراضي مفروض | No forced default

**الوكيل هو اللي بيختار الخط الأكثر جاذبية ومناسبة للريل** — عربي أو إنجليزي — لكل مشهد/عنصر،
وبيسجّل اختياره في `plan/text-direction.json` (`fontStyles` لكل دور + `fontElements` لأي عنصر
محتاج خط خاص) مع تبرير قصير. Cairo وInter مجرد **شبكة أمان** لكروم النظام (preview/progress)،
مش قرار إبداعي مفروض. اللينت T05 وبوابات الرندر بيرفضوا أي نص من غير خط مختار صريح.

قواعد إبداعية: اختار **زوج** عربي/لاتيني بنفس الإحساس، وحافظ على تشكيل الكلمة كاملة،
ويفضّل ما تزيدش عن عيلتين في المشهد إلا لسبب متسجّل.

### عربي | Arabic

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

## مرفوض | Tested and rejected

- **Reem Kufi** — شكلها حلو، بس في الترجمة اللي على npm أوزان الحروف بتبقى أضيق من الرسم، فالكلمات
  بتتراكب مع بعضها عندنا (HarfBuzz). الرقم: نسبة تراكب 0.27 مقابل ≤ 0.14 لأي عيلة سليمة — وده بقى
  حاجز في `tests/test_fonts.py` (`audio` → `type`)، فأي عيلة جديدة بتتراكب هتتوقف عند البوابة.
- **Noto Kufi Arabic** و**Reem Kufi Fun** و**Jomhuria** — نفس المشكلة: الـstatic instances بتتراكب
  (0.22 / 0.27 / 0.50). استبدلناهم بـ**Lalezar** (تراكب 0.11) للبوستر التقيل.
- **خطوط بترخيص مش OFL** (زي أسماء تجارية كتير على الإنترنت) — ممنوعة، حتى لو مجانية للاستخدام الشخصي.
- **خطوط متغيّرة (variable)** — مقبولة تقنيًا، بس بنستخدم Instances ساكنة: أنسب للرندر الأوفلاين
  وبيمنع مفاجآت في الأوزان بين Pillow وChromium.

## الترخيص | Licence

كل عيلة معاها `OFL.txt` في فولدرها (`assets/fonts/<Family>/OFL.txt`)، وكلها مسجّلة في
`assets/CREDITS.md`. الـOFL بيسمح بالاستخدام التجاري والتعديل وإعادة التوزيع؛ لو عدّلت ملف خط،
لازم تغيّر اسمه (شرط في الرخصة) — إحنا مش بنعدّل، بنستخدم زي ما هو.
