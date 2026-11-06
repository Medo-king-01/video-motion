# الخطوط — Type system

**123 عيلة خط، كلها مجانية (SIL OFL 1.1):** استخدام تجاري، إعادة توزيع، ومن غير أي إتاوة أو حقوق على
الشاشة. مفيش خط مدفوع ولا خط محتاج ترخيص منفصل — ودي ميزة مش تفصيلة: أي ريل بيطلع من هنا يقدر يتسلّم
لعميل أو يتنشر مدفوع من غير سؤال.

منهم **٢١ عيلة مختارة للكابشن** (جدولَي عربي/إنجليزي تحت) والباقي **موسّع pool** بجدول مولّد تحت.
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

## الموسّع | Expanded pool (102 عيلة — 2026-11-06)

جدول مولّد من `assets/fonts/fonts.json`. كل عيلة هنا معاها `OFL.txt` وملفاتها متحقّق منها في
`tools/fonts_install.py --check`؛ اللي عليها ❌ اتقيست واتأكدت بصريًا إنها بتزوّد الكلمات على بعضها
فممنوعة من الكابشن والبودي (تقدر تيجي ديسبلاي لكلمة واحدة بعد معاينة `make fonts-sheet`).

| العيلة | السكربت | الأوزان | caption-safe | tags | المصدر |
|---|---|---|---|---|---|
| **Alan Sans** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Alan+Sans |
| **Alkalami** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Alkalami |
| **Alyamama** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Alyamama |
| **Amiri Quran** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Amiri+Quran |
| **Aref Ruqaa** | arabic | 700/400 | ❌ display only | display, additional | https://fonts.google.com/specimen/Aref+Ruqaa |
| **Aref Ruqaa Ink** | arabic | 700/400 | ❌ display only | display, additional | https://fonts.google.com/specimen/Aref+Ruqaa+Ink |
| **Badeen Display** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Badeen+Display |
| **Baloo Bhaijaan 2** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Baloo+Bhaijaan+2 |
| **Beiruti** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Beiruti |
| **Blaka** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Blaka |
| **Blaka Hollow** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Blaka+Hollow |
| **Blaka Ink** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Blaka+Ink |
| **Cairo Play** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Cairo+Play |
| **Cascadia Code** | arabic | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Cascadia+Code |
| **Cascadia Mono** | arabic | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Cascadia+Mono |
| **Estedad** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Estedad |
| **Firjar** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Firjar |
| **Fustat** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Fustat |
| **Gulzar** | arabic | 400 | ❌ display only | display, additional | https://fonts.google.com/specimen/Gulzar |
| **Handjet** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Handjet |
| **Harmattan** | arabic | 700/500/400/700 | ✅ | sans, additional | https://fonts.google.com/specimen/Harmattan |
| **Jomhuria** | arabic | 400 | ❌ display only | display, additional | https://fonts.google.com/specimen/Jomhuria |
| **Katibeh** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Katibeh |
| **Lateef** | arabic | 700/700/300/300/500/400/700 | ✅ | display, additional | https://fonts.google.com/specimen/Lateef |
| **Lemonada** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Lemonada |
| **Mada** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Mada |
| **Marhey** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Marhey |
| **Markazi Text** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Markazi+Text |
| **Mirza** | arabic | 700/500/400/700 | ✅ | display, additional | https://fonts.google.com/specimen/Mirza |
| **Noto Kufi Arabic** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Noto+Kufi+Arabic |
| **Noto Naskh Arabic** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Noto+Naskh+Arabic |
| **Noto Naskh Arabic UI** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Noto+Naskh+Arabic+UI |
| **Noto Nastaliq Urdu** | arabic | 400 | ❌ display only | display, additional | https://fonts.google.com/specimen/Noto+Nastaliq+Urdu |
| **Noto Sans Arabic** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Noto+Sans+Arabic |
| **Noto Sans Arabic UI** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Noto+Sans+Arabic+UI |
| **Oi** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Oi |
| **Parastoo** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Parastoo |
| **Playpen Sans Arabic** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Playpen+Sans+Arabic |
| **Qahiri** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Qahiri |
| **Rakkas** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Rakkas |
| **Reem Kufi** | arabic | 400 | ❌ display only | sans, additional | https://fonts.google.com/specimen/Reem+Kufi |
| **Reem Kufi Fun** | arabic | 400 | ❌ display only | sans, additional | https://fonts.google.com/specimen/Reem+Kufi+Fun |
| **Reem Kufi Ink** | arabic | 400 | ❌ display only | sans, additional | https://fonts.google.com/specimen/Reem+Kufi+Ink |
| **Ruwudu** | arabic | 700/500/400/700 | ✅ | display, additional | https://fonts.google.com/specimen/Ruwudu |
| **Scheherazade New** | arabic | 700/500/400/700 | ✅ | display, additional | https://fonts.google.com/specimen/Scheherazade+New |
| **Thabit** | arabic | 700/700/400/400 | ✅ | display, additional | https://fonts.google.com/specimen/Thabit |
| **Vazirmatn** | arabic | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Vazirmatn |
| **Vibes** | arabic | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Vibes |
| **Zain** | arabic | 900/700/700/300/400/300/300/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Zain |
| **Abril Fatface** | latin | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Abril+Fatface |
| **Archivo** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Archivo |
| **Audiowide** | latin | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Audiowide |
| **Bangers** | latin | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Bangers |
| **Barlow** | latin | 900/900/700/700/700/700/300/300/400/300/300/500/500/400/700/700/100/100 | ✅ | sans, additional | https://fonts.google.com/specimen/Barlow |
| **Barlow Condensed** | latin | 900/900/700/700/700/700/300/300/400/300/300/500/500/400/700/700/100/100 | ✅ | sans, additional | https://fonts.google.com/specimen/Barlow+Condensed |
| **Bricolage Grotesque** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Bricolage+Grotesque |
| **Caveat** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Caveat |
| **Chakra Petch** | latin | 700/700/300/300/400/300/300/500/500/400/700/700 | ✅ | sans, additional | https://fonts.google.com/specimen/Chakra+Petch |
| **Chivo** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Chivo |
| **Cormorant Garamond** | latin | 400/400 | ✅ | display, additional | https://fonts.google.com/specimen/Cormorant+Garamond |
| **Dancing Script** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Dancing+Script |
| **DM Sans** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/DM+Sans |
| **DM Serif Display** | latin | 400/400 | ✅ | display, additional | https://fonts.google.com/specimen/DM+Serif+Display |
| **Exo 2** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Exo+2 |
| **Fira Code** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Fira+Code |
| **Fira Sans** | latin | 900/700/900/700/700/700/300/300/400/300/300/500/500/400/700/700/100/100 | ✅ | sans, additional | https://fonts.google.com/specimen/Fira+Sans |
| **Fraunces** | latin | 400/400 | ✅ | display, additional | https://fonts.google.com/specimen/Fraunces |
| **IBM Plex Serif** | latin | 700/700/300/300/400/300/300/500/500/400/700/700/100/100 | ✅ | display, additional | https://fonts.google.com/specimen/IBM+Plex+Serif |
| **JetBrains Mono** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/JetBrains+Mono |
| **Josefin Sans** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Josefin+Sans |
| **Jost** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Jost |
| **Lexend** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Lexend |
| **Libre Baskerville** | latin | 400/400 | ✅ | display, additional | https://fonts.google.com/specimen/Libre+Baskerville |
| **Lobster** | latin | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Lobster |
| **Lora** | latin | 400/400 | ✅ | display, additional | https://fonts.google.com/specimen/Lora |
| **Manrope** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Manrope |
| **Merriweather** | latin | 400/400 | ✅ | display, additional | https://fonts.google.com/specimen/Merriweather |
| **Michroma** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Michroma |
| **Monoton** | latin | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Monoton |
| **Montserrat** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Montserrat |
| **Nunito** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Nunito |
| **Open Sans** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Open+Sans |
| **Orbitron** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Orbitron |
| **Oswald** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Oswald |
| **Outfit** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Outfit |
| **Pacifico** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Pacifico |
| **Playfair Display** | latin | 400/400 | ✅ | display, additional | https://fonts.google.com/specimen/Playfair+Display |
| **Plus Jakarta Sans** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Plus+Jakarta+Sans |
| **Poppins** | latin | 900/700/900/700/700/700/300/300/400/300/300/500/500/400/700/700/100/100 | ✅ | sans, additional | https://fonts.google.com/specimen/Poppins |
| **Quicksand** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Quicksand |
| **Rajdhani** | latin | 700/300/500/400/700 | ✅ | sans, additional | https://fonts.google.com/specimen/Rajdhani |
| **Raleway** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Raleway |
| **Righteous** | latin | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Righteous |
| **Roboto** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Roboto |
| **Russo One** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Russo+One |
| **Source Sans 3** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Source+Sans+3 |
| **Space Mono** | latin | 700/400/700/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Space+Mono |
| **Syne** | latin | 400 | ✅ | display, additional | https://fonts.google.com/specimen/Syne |
| **Tektur** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Tektur |
| **Unbounded** | latin | 400 | ✅ | sans, additional | https://fonts.google.com/specimen/Unbounded |
| **Urbanist** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Urbanist |
| **Work Sans** | latin | 400/400 | ✅ | sans, additional | https://fonts.google.com/specimen/Work+Sans |

## قياس التشكيل | Measured shaping (بوابة التراكب)

البوابة في `tests/test_fonts.py` بتقيس تراكب حبر الحروف بعد تشكيل HarfBuzz لكلمة «النهاردة» بكل وزن.
الحد **0.28**: الحروف العربية المتصلة بتخلي الأرقام السليمة تقع بين 0.03 و0.27، والعيلات المرفوضة
اتقيست 0.24–0.50 **واتأكدت بصريًا** (cache/font-collision-sheet.png) قبل ما تتعلّم captionSafe=false.
أي عيلة جديدة فوق الحد بتوقف البوابة لحد ما تتقاس وتتشاف.

| العيلة | أسوأ تراكب مقاس | الحكم |
|---|---|---|
| Jomhuria | 0.495 | مرفوض للكابشن (captionSafe=false) |
| Aref Ruqaa | 0.421 | مرفوض للكابشن (captionSafe=false) |
| Noto Nastaliq Urdu | 0.371 | مرفوض للكابشن (captionSafe=false) |
| Aref Ruqaa Ink | 0.342 | مرفوض للكابشن (captionSafe=false) |
| Gulzar | 0.317 | مرفوض للكابشن (captionSafe=false) |
| Noto Sans Arabic | 0.272 | سليم للكابشن |
| Estedad | 0.247 | سليم للكابشن |
| Reem Kufi | 0.247 | مرفوض للكابشن (captionSafe=false) |
| Reem Kufi Fun | 0.247 | مرفوض للكابشن (captionSafe=false) |
| Mirza | 0.246 | سليم للكابشن |
| Reem Kufi Ink | 0.241 | مرفوض للكابشن (captionSafe=false) |
| Noto Naskh Arabic | 0.231 | سليم للكابشن |
| Noto Kufi Arabic | 0.223 | سليم للكابشن |
| Katibeh | 0.214 | سليم للكابشن |
| Fustat | 0.207 | سليم للكابشن |
| Scheherazade New | 0.197 | سليم للكابشن |
| Mada | 0.188 | سليم للكابشن |
| Lateef | 0.187 | سليم للكابشن |
| Amiri | 0.142 | سليم للكابشن |
| Alkalami | 0.141 | سليم للكابشن |
| Ruwudu | 0.141 | سليم للكابشن |
| Qahiri | 0.129 | سليم للكابشن |
| Lalezar | 0.111 | سليم للكابشن |
| Blaka | 0.110 | سليم للكابشن |
| Blaka Hollow | 0.110 | سليم للكابشن |
| Blaka Ink | 0.110 | سليم للكابشن |
| Playpen Sans Arabic | 0.110 | سليم للكابشن |
| Markazi Text | 0.106 | سليم للكابشن |
| Harmattan | 0.100 | سليم للكابشن |
| Amiri Quran | 0.094 | سليم للكابشن |
| Rubik | 0.080 | سليم للكابشن |
| Baloo Bhaijaan 2 | 0.077 | سليم للكابشن |
| Tajawal | 0.076 | سليم للكابشن |
| Lemonada | 0.075 | سليم للكابشن |
| Noto Sans Arabic UI | 0.073 | سليم للكابشن |
| Parastoo | 0.072 | سليم للكابشن |
| IBM Plex Sans Arabic | 0.069 | سليم للكابشن |
| Cairo | 0.068 | سليم للكابشن |
| El Messiri | 0.068 | سليم للكابشن |
| Cairo Play | 0.068 | سليم للكابشن |
| Rakkas | 0.068 | سليم للكابشن |
| Alyamama | 0.064 | سليم للكابشن |
| Changa | 0.061 | سليم للكابشن |
| Vazirmatn | 0.060 | سليم للكابشن |
| Vibes | 0.060 | سليم للكابشن |
| Zain | 0.058 | سليم للكابشن |
| Readex Pro | 0.057 | سليم للكابشن |
| Alexandria | 0.054 | سليم للكابشن |
| Cascadia Code | 0.052 | سليم للكابشن |
| Cascadia Mono | 0.052 | سليم للكابشن |
| Thabit | 0.049 | سليم للكابشن |
| Beiruti | 0.046 | سليم للكابشن |
| Kufam | 0.043 | سليم للكابشن |
| Firjar | 0.043 | سليم للكابشن |
| Marhey | 0.041 | سليم للكابشن |
| Alan Sans | 0.040 | سليم للكابشن |
| Almarai | 0.036 | سليم للكابشن |
| Noto Naskh Arabic UI | 0.036 | سليم للكابشن |
| Oi | 0.035 | سليم للكابشن |
| Badeen Display | 0.029 | سليم للكابشن |
| Handjet | 0.004 | سليم للكابشن |

## مرفوض | Tested and rejected

- **Permanent Marker** و**Ubuntu** — وصلوا في توسعة 2026-11-06 من غير `OFL.txt`، وترخيصهم الأصلي مش SIL OFL 1.1 (Apache-2.0 / Ubuntu Font Licence)، فاتشالوا من قائمة المسموح على الشاشة؛ الاستوديو بيسلّم شغل عملاء بوعد OFL بس.
- **Jomhuria · Aref Ruqaa · Aref Ruqaa Ink · Gulzar · Noto Nastaliq Urdu · Reem Kufi · Reem Kufi Fun · Reem Kufi Ink** — تراكب مقاس 0.24–0.50 ومؤكد بصريًا: الكلمات بتدخل في بعضها بعد التشكيل. متعلّمين `captionSafe: false` في المانيفست فالبوابة بتعديهم بس الاختيار للكابشن ممنوع.
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

## التحقق ومصدر التنزيل المقفول

`python3 tools/fonts_install.py --check` فحص read-only لكل عائلة ووزن وملف TTF وOFL فعلي.
القائمة المتوقعة في `FAMILIES` هي نفس اللي بيستخدمها doctor وsetup، مش حد أدنى ثابت للعدد.
التنزيل بيستخدم إصدارات npm وSHA-512 في `tools/font-packages.lock.json`؛ أي checksum مختلف بيوقف التثبيت.
تحديث ملف القفل قرار مقصود لازم بعده مراجعة OFL وتشغيل اختبارات الخطوط والرندر؛ مش بيغير الملفات المضمّنة لوحده.
