# نظام الستايلات — Visual Styles

## نظرة عامة

**17 ستايل بصري** للفيديو، مستوحاة من [Majed Video](https://github.com/majedphotos/video-ad-editor). كل ستايل يعرّف اللغة البصرية الكاملة للفيديو: باليت ألوان، خطوط، سطح، شخصية.

## الاستخدام

في `BRIEF.md` أو `project.json`:
```json
{
  "style": "paperCut"
}
```

أو دمج ستايلين:
```json
{
  "style": "explainer+keynote"
}
```

## الستايلات المتاحة

### 🎤 keynote — كينوت
فراغ كبير، كلمة وحدة تحمل المشهد، حركة قليلة مضبوطة
- **باليت:** أبيض رمادي (#F5F5F7) + برتقالي (#D97757)
- **خطوط:** IBM Plex Sans Arabic + Inter
- **شخصية:** clean
- **مناسب لـ:** reveal, number, launch, calm

### 💎 glassUI — زجاج الواجهة
إشعارات وكروت وويدجت بمادة زجاجية فوق الفيديو
- **باليت:** داكن (#0E1116) + أبيض
- **خطوط:** Readex Pro + Inter
- **شخصية:** organic
- **مناسب لـ:** tech, app, list, chat

### 📰 explainer — شرح صحفي
ورق ودبابيس وقلم تحديد وخيط أحمر — المعلومة تطلع موثّقة
- **باليت:** ورق (#EDE5D3) + أصفر (#FFE14D) + أحمر (#C8382B)
- **خطوط:** Aref Ruqaa + IBM Plex Sans Arabic
- **شخصية:** organic
- **مناسب لـ:** news, number, contrast, map, source

### ✂️ paperCut — ورق مقصوص
كل شي قصاصة ورق بحد أبيض وظل قاسي — ستوب موشن
- **باليت:** كرافت (#E7D7B5) + أحمر (#E2482B) + أصفر (#F2C230)
- **خطوط:** Lalezar + IBM Plex Sans Arabic
- **شخصية:** snappy
- **FPS:** 12 (ستوب موشن)
- **مناسب لـ:** hit, list, fun, emphasis

### 📼 archive — وثائقي
حبيبات فلم، ملف مانيلا، آلة كاتبة، ختم أحمر
- **باليت:** بني داكن (#2A231A) + أحمر (#B3261E) + بيج (#D9C59A)
- **خطوط:** Aref Ruqaa + IBM Plex Sans Arabic
- **شخصية:** calm
- **مناسب لـ:** story, history, reveal, secret, date

### 📖 editorial — مجلة
غلاف مجلة: عنوان ضخم ورا الراس، خطوط رفيعة
- **باليت:** بيج (#F1ECE3) + أحمر (#C8382B)
- **خطوط:** Aref Ruqaa + IBM Plex Sans Arabic
- **شخصية:** clean
- **مناسب لـ:** quote, profile, story, title

### 🔴 swiss — سويسري
شبكة صارمة، أحمر وأسود وأبيض، بلا زخرفة
- **باليت:** أبيض + أسود + أحمر (#E30613)
- **خطوط:** Noto Kufi Arabic + IBM Plex Sans Arabic
- **شخصية:** clean
- **مناسب لـ:** number, list, steps, data

### ✏️ doodle — رسم يد
أسهم ودوائر بقلم تنرسم وهي تلحق الكلام
- **باليت:** أبيض (#FBFAF6) + برتقالي (#D97757)
- **خطوط:** Aref Ruqaa + IBM Plex Sans Arabic
- **شخصية:** organic
- **مناسب لـ:** emphasis, explain, arrow, tip

### 💻 terminal — تيرمنال
نافذة كود داكنة، مؤشر يومض، أوامر تنكتب
- **باليت:** داكن (#0D1117) + أخضر (#3FB950) + بنفسجي (#D2A8FF)
- **خطوط:** IBM Plex Sans Arabic + monospace
- **شخصية:** mechanical
- **مناسب لـ:** tech, code, ai, tool

### 🎨 riso — ريزو
حبرين فلورسنت متراكبين مزحزحين، طباعة يدوية
- **باليت:** بيج (#F4F0E8) + وردي (#FF48B0) + سماوي (#00A9B5)
- **خطوط:** Lalezar + IBM Plex Sans Arabic
- **شخصية:** snappy
- **مناسب لـ:** hook, title, fun

### 📄 newsprint — جريدة
ورق جرايد، عنوان عريض، أعمدة رفيعة
- **باليت:** ورق (#E9E5DC) + أحمر (#C8102E)
- **خطوط:** Aref Ruqaa + IBM Plex Sans Arabic
- **شخصية:** clean
- **مناسب لـ:** news, breaking, source

### 📐 blueprint — بلوبرنت
أزرق وشبكة قياس، خطوط تنرسم وأسهم أبعاد
- **باليت:** أزرق (#1E4C8F) + برتقالي (#FF9F43)
- **خطوط:** Noto Kufi Arabic + Readex Pro
- **شخصية:** calm
- **مناسب لـ:** how, explain, parts, tech

### 📺 vhs — VHS
شاشة قديمة: خطوط مسح ونزيف ألوان
- **باليت:** داكن (#0A0A12) + أخضر (#33FF66) + وردي (#FF3366)
- **خطوط:** Noto Kufi Arabic + monospace
- **شخصية:** mechanical
- **مناسب لـ:** flashback, old, retro
- **ملاحظة:** للحظات قصيرة بس

### ⚡ brutal — بروتالي
ألوان صارخة، حدود سودة عريضة وظل قاسي
- **باليت:** أصفر (#FFE600) + أسود + أحمر (#FF3B00)
- **خطوط:** Lalezar + IBM Plex Sans Arabic
- **شخصية:** snappy
- **مناسب لـ:** hook, cta, hit
- **ملاحظة:** للهوك والطلب بس

### 🎬 studio3D — ستوديو منتج
خلفية كريمية بإضاءة ناعمة، اسم بارز
- **باليت:** كريمي (#EFE7DA) + برتقالي (#D97757)
- **خطوط:** Cairo + IBM Plex Sans Arabic
- **شخصية:** calm
- **مناسب لـ:** launch, tool, free, name

### 🎭 stickerToon — ستيكر كرتوني
باستيل وحدود سودة، فقاعات وماسكوت ينط
- **باليت:** وردي (#F7C6D9) + برتقالي (#FF7A1A) + أزرق (#CFE6FF)
- **خطوط:** Lalezar + IBM Plex Sans Arabic
- **شخصية:** bouncy
- **FPS:** 12
- **مناسب لـ:** fun, tool, explain, kids

### 💳 devCard — كرت أداة
كريمي بشبكة وأشعة، كرت أبيض، breadcrumb
- **باليت:** كريمي (#F4EFE6) + برتقالي (#C8643B)
- **خطوط:** IBM Plex Sans Arabic + Aref Ruqaa
- **شخصية:** clean
- **مناسب لـ:** tool, skill, free, launch, fact

---

## العائلات (Families)

كل ستايل ينتمي لعائلة أو أكثر:

| العائلة | الوصف |
|---------|-------|
| **calm** | هادي — جمل تأمل ونصايح |
| **punch** | طاقة — هوك قوي، أرقام، مقارنات |
| **onetake** | ونشوت — كاميرا مستمرة بلا قص |
| **editorial** | تحريري — شرح وقوائم ومعلومة |

## الشخصيات (Personalities)

كل ستايل له شخصية تحدد إيزنق الحركات:

| الشخصية | الإيزنق | الوصف |
|---------|---------|-------|
| **calm** | sineInOut | هادئ |
| **clean** | expoOut | نظيف |
| **snappy** | backOut | حاد |
| **bouncy** | backOut | نطاط |
| **mechanical** | stepped | آلي |
| **organic** | softBack | عضوي |
| **soft** | cubicOut | ناعم |

## الدمج (Blending)

يمكن دمج ستايلين:
```json
{
  "style": "explainer+keynote"
}
```

الدمج يأخذ:
- **السطح** من الأول
- **الكرت والتسمية** من الثاني
- **الباليت** من الأول (يمكن تخصيصه)

## المصادر

مستوحى من [Majed Video](https://github.com/majedphotos/video-ad-editor) — بلقن تحرير فيديو لـ Claude Code.

---

## الملف

البيانات في `assets/styles/styles.json`
