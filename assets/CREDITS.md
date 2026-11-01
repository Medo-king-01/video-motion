# الأصول الخارجية — Credits

> كل أصل مش متولّد بكود لازم يتسجّل هنا: الاسم · المصدر · الترخيص · التاريخ · فين مستخدم.

| الأصل | المصدر | الترخيص | التاريخ | الاستخدام |
|---|---|---|---|---|
| خط Cairo | Google Fonts (OFL) | SIL OFL 1.1 | 2026-10 | كل النصوص العربية على الشاشة |
| خط Tajawal | fonts.google.com/specimen/Tajawal · npm `@expo-google-fonts/tajawal` | SIL OFL 1.1 | 2026-11-01 | geometric headlines and numbers (`docs/fonts.md`) |
| خط IBM Plex Sans Arabic | fonts.google.com/specimen/IBM+Plex+Sans+Arabic · npm `@expo-google-fonts/ibm-plex-sans-arabic` | SIL OFL 1.1 | 2026-11-01 | technical / UI / telemetry (`docs/fonts.md`) |
| خط Almarai | fonts.google.com/specimen/Almarai · npm `@expo-google-fonts/almarai` | SIL OFL 1.1 | 2026-11-01 | small captions and long body where legibility beats personality (`docs/fonts.md`) |
| خط Alexandria | fonts.google.com/specimen/Alexandria · npm `@expo-google-fonts/alexandria` | SIL OFL 1.1 | 2026-11-01 | big display Arabic (hook word, key number) (`docs/fonts.md`) |
| خط Kufam | fonts.google.com/specimen/Kufam · npm `@expo-google-fonts/kufam` | SIL OFL 1.1 | 2026-11-01 | kufic-geometric statement (`docs/fonts.md`) |
| خط El Messiri | fonts.google.com/specimen/El+Messiri · npm `@expo-google-fonts/el-messiri` | SIL OFL 1.1 | 2026-11-01 | Egyptian-flavoured modern display (`docs/fonts.md`) |
| خط Amiri | fonts.google.com/specimen/Amiri · npm `@expo-google-fonts/amiri` | SIL OFL 1.1 | 2026-11-01 | naskh serif (`docs/fonts.md`) |
| خط Inter | fonts.google.com/specimen/Inter · npm `@expo-google-fonts/inter` | SIL OFL 1.1 | 2026-11-01 | Latin default (`docs/fonts.md`) |
| خط Space Grotesk | fonts.google.com/specimen/Space+Grotesk · npm `@expo-google-fonts/space-grotesk` | SIL OFL 1.1 | 2026-11-01 | technical display (`docs/fonts.md`) |
| خط IBM Plex Sans | fonts.google.com/specimen/IBM+Plex+Sans · npm `@expo-google-fonts/ibm-plex-sans` | SIL OFL 1.1 | 2026-11-01 | Latin half of the Plex superfamily (`docs/fonts.md`) |
| خط IBM Plex Mono | fonts.google.com/specimen/IBM+Plex+Mono · npm `@expo-google-fonts/ibm-plex-mono` | SIL OFL 1.1 | 2026-11-01 | code, specs, numbers that must line up (`docs/fonts.md`) |
| خط Anton | fonts.google.com/specimen/Anton · npm `@expo-google-fonts/anton` | SIL OFL 1.1 | 2026-11-01 | one heavy display weight (`docs/fonts.md`) |
| خط Instrument Serif | fonts.google.com/specimen/Instrument+Serif · npm `@expo-google-fonts/instrument-serif` | SIL OFL 1.1 | 2026-11-01 | editorial serif (`docs/fonts.md`) |
| أيقونات itshover (263 أيقونة) | https://itshover.com · https://github.com/itshover/itshover | **Apache-2.0** | 2026-11-01 | `medo-motion/icons/itshover/tsx/` — مولّد منها أيقونات المحركين. نص الترخيص في `medo-motion/icons/itshover/LICENSE` |

## Type system — `assets/fonts/` (14 families, SIL OFL 1.1)
كل العيلات من Google Fonts، اتسحبت كـTTF من حزم npm `@expo-google-fonts/*` بـ`tools/fonts_install.py`،
وكل عيلة معاها `OFL.txt` في فولدرها. الـOFL بيسمح بالاستخدام التجاري وإعادة التوزيع من غير أي حقوق
على الشاشة؛ لو عدّلت ملف خط لازم تغيّر اسمه. **مفيش خط مدفوع أو محتاج ترخيص منفصل في المشروع.**

## ملاحظات
- **العلامات التجارية:** أيقونات البراند (Google / Apple / Notion / OpenAI …) هي علامات مسجّلة لأصحابها. وجودها في المكتبة لا يعني
  حق استخدامها كهوية. المجموعة معلّمة في الـregistry بـ`group: "brand"`، وممنوع استخدامها في ريلز ميدو من غير موافقته، وممنوع تمامًا
  استخدامها كشعار للاستوديو (الاستوديو أصلًا مفيش ليه لوجو).
- أي أصل جديد: يتسجّل هنا قبل ما يتحط في `projects/<slug>/assets/`.

## Presenter poses — `assets/poses/`
أصل مملوك لصاحب المشروع (اتسلّم ٢٠٢٦-١١-٠١)، مش من مكتبة خارجية. الأصل في `raw/` والنسخ المقصوصة
+ `poses.json` مولّدة بـ`tools/presenter_build.py` (قص خلفية + تطبيع). لو حبيت تنشر، الحقوق محفوظة
لصاحب المشروع.
