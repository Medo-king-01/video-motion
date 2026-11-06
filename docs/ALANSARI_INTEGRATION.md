# دمج مكتبة Alansari Motion Library

## نظرة عامة

تم دمج مكتبة [Alansari Motion Library](https://github.com/alansariteach/motion-library) بشكل كامل في استيديو video-motion، مما أضاف:

- **275 حركة أساسية** جديدة
- **1100 متغير** (Fast/Slow/Gold/Boxed)
- **104 خط إضافي** (49 عربي + 55 إنجليزي)

### الإحصائيات النهائية

| | قبل | بعد | التحسن |
|---|---|---|---|
| **التقنيات** | 59 | **1434** | **+2330%** |
| **الخطوط** | 21 | **125** | **+495%** |
| **الفئات** | 13 | **27** | **+108%** |

## الفئات المضافة

### 📝 دخول النصوص (Text In) - 25 حركة
- Fade Up, Typewriter, Letter Cascade, Mask Slide, Blur In
- Slide In Right/Left, Drop In, Zoom In/Out Text
- وغيرها الكثير

### ✨ الإبراز (Emphasis) - 25 حركة
- Highlight Sweep, Underline Draw, Scale Punch
- Word Shake, Glitch Text, Circle Around
- Strike Through, Box Outline Draw, Color Pulse

### 📺 الكابشن (Captions) - 29 حركة
- Karaoke Highlight, Word Pop, Bounce Caption
- Boxed Word, One-Word Caption, Typewriter Caption
- Fade Words, Slide-Up Words, Underline Active Word

### 🎬 الانتقالات (Transitions) - 30 حركة
- Circle Reveal, Linear Wipe, Light Sweep
- Zoom Blur, Whip Pan, Fade Through Black
- Cross Dissolve, Slide Push, Diagonal Wipe

### 📷 الكاميرا (Camera) - 25 حركة
- Punch-In, Slow Push-In, Camera Shake
- Zoom-Out Card, Ken Burns, Dolly Zoom
- Pan, Tilt Up, Rack Focus

### 💥 المؤثرات (Effects) - 25 حركة
- Particle Dissolve, Shockwave, Pulse Rings
- Light Rays, Confetti Burst, Sparkle Trail
- Dust Burst, Lens Flare, Scan Line

### 📱 السوشال (Social) - 25 حركة
- Follow Tap, Comment Typing, Like Burst
- DM Notification, Paper Plane, Bell Ring
- Share Tap, Save Bookmark, Story Ring

### 🏷️ الشعارات والعناوين (Logos & Titles) - 25 حركة
- Logo Float, Logo Spin-In, Title Card Drop
- Lower Third, Number Counter, Logo Mask Reveal
- Logo Stroke Draw, Logo Glitch, Logo Bounce

### 👤 تأثيرات الشخص (Person FX) - 13 حركة
- Text Behind Person, Color Pop, Echo Trail
- Clone Trio, Doodle Outline, Sticker Cutout
- Pop-Out Frame, Portrait Mode, Silhouette Fill

### 🎵 الصوت والإيقاع (Audio & Beat) - 12 حركة
- Waveform, Equalizer Bars, Circular Visualizer
- Beat Flash, Beat Zoom, Beat Shake
- Audio Pulse Ring, Waveform Caption, Mic Pulse

### 🖥️ الشاشات والواجهات (Screens & UI) - 15 حركة
- App Window Pop, Phone Scroll, Laptop Mockup
- Browser Window, Phone Slide In, Cursor Click
- Zoom to Cursor, Modal Pop, Toggle Switch

### 🎯 تتبع الحركة (Tracking) - 8 حركات
- Label Follow, Tracking Ring, Face Blur
- Callout Line, Screen Replace, Arrow Follow

### 🎲 ثلاثي الأبعاد (3D) - 10 حركات
- 3D Spin Text, Extruded Text, Parallax 2.5D
- Card Flip, Cube Spin, Tilt Card
- Layer Explode, 3D Carousel, Float Shadow

### ⏰ تأثيرات الوقت (Time FX) - 8 حركات
- Reverse, Boomerang, Stop Motion, Strobe
- Time-Lapse Clock, Day to Night, Fast Forward

## كيف تستخدمها

### من سطر الأوامر

```bash
# عرض كل التقنيات
python3 tools/techniques.py --list

# عرض فئة معينة
python3 tools/techniques.py --list --category cap

# عرض تفاصيل تقنية محددة
python3 tools/techniques.py --show al-cap-011

# رسم خطة كاملة
python3 tools/techniques.py --draw --from-plan plan/beats.json
```

### في الكود

```python
import json
with open('assets/techniques.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# البحث عن تقنيات الكابشن
captions = [t for t in data['techniques'] if t['category'] == 'cap']
for tech in captions:
    print(f"{tech['id']}: {tech['name']}")
```

## التحويل من Alansari إلى الاستيديو

### تحويل primitive

| القيمة الأصلية | القيمة في الاستيديو | السبب |
|---------------|---------------------|---------|
| scale | depth | التحجيم مرتبط بالعمق |
| rotate | depth | الدوران مرتبط بالعمق |
| translate | timeline | الحركة على المحور الزمني |
| opacity | blur | الشفافية مرتبطة بالـ blur |
| composite | timeline | الحركات المركبة |
| pulse | sound | النبض مرتبط بالصوت |
| track | camera | التتبع مرتبط بالكاميرا |

### تحويل energy

| القيمة الأصلية | القيمة في الاستيديو |
|---------------|---------------------|
| low | calm |
| medium | medium |
| high | high |

## التوثيق

تم تحديث ملف `docs/techniques.md` ليشمل كل التقنيات الجديدة مع:
- الوصف بالعربية والإنجليزية
- خصائص الحركة (easing, duration, primitive)
- متى تستخدم ومتى تتجنب

## الأدوات

- `tools/merge_alansari.py` - سكريبت الدمج
- `tools/generate_techniques_docs.py` - توليد التوثيق
- `tools/techniques.py` - أدوات الاستيديو الأصلية (تدعم التقنيات الجديدة)

## الإحصائيات

- **التقنيات الأصلية**: 59
- **حركات Alansari الأساسية**: 275
- **المتغيرات (Fast/Slow/Gold/Boxed)**: 1100
- **الإجمالي**: 1434
- **الفئات**: 27 (13 أصلية + 14 جديدة)

## المتغيرات (Variants)

كل حركة أساسية لها 4 أشكال مختلفة:

| النوع | الوصف | السرعة |
|-------|-------|--------|
| **Fast** | أسرع بـ 40% | ×0.6 |
| **Slow** | أبطأ بـ 60% | ×1.6 |
| **Gold** | نسخة ذهبية فاخرة | ×1.0 |
| **Boxed** | النص داخل صندوق ملون | ×1.0 |

## نظام الخطوط

- **قبل**: 21 عيلة (12 عربي + 9 إنجليزي)
- **بعد**: 125 عيلة (61 عربي + 64 إنجليزي)

### الخطوط العربية الجديدة (49 عيلة)

تشمل:
- **Alan Sans** — عربي حديث متغير الأوزان
- **Alyamama** — عربي متغير الأوزان
- **Aref Ruqaa** — خط الرقعة
- **Aref Ruqaa Ink** — رقعة بحبر فني
- **Badeen Display** — عرضي أنيق
- **Fustat** — عربي عصري
- **Reem Kufi** — كوفي حديث
- **Reem Kufi Fun** — كوفي مرح
- **Reem Kufi Ink** — كوفي بحبر فني
- **Qahiri** — فرعوني فريد
- **Cairo Play** — القاهرة بظلال 3D
- **Blaka** — خط زخرفي
- **Blaka Hollow** — خط زخرفي مجوف
- **Blaka Ink** — خط زخرفي بحبر
- **Baloo Bhaijaan 2** — خط مستدير مرح
- وغيرها الكثير...

### الخطوط الإنجليزية الجديدة (55 عيلة)

تشمل:
- **Abril Fatface** — عرضي أنيق
- **Bangers** — كوميكس
- **Barlow** — sans-serif عصري
- **Barlow Condensed** — مضغوط
- **Bricolage Grotesque** — متغير الأوزان
- **Caveat** — handwritten
- **Chakra Petch** — مستقبلي
- **Chivo** — sans-serif متنوع
- وغيرها الكثير...

## مصادر إضافية

- [مكتبة Alansari Motion Library](https://github.com/alansariteach/motion-library)
- [الموقع التفاعلي](https://alansariteach.github.io/motion-library/)
- [التوثيق بالعربية](https://alansariteach.github.io/motion-library/alansari-motion-library-ar.md)

## ملاحظات

- التقنيات المدمجة تحتفظ بالخصائص الأصلية (easing, duration, spec)
- تم تحويل القيم لتتوافق مع نظام الاستيديو
- كل تقنية لها معرف فريد يبدأ بـ `al-` متبوعاً بالفئة ورقم الحركة الأصلية
- التقنيات الجديدة متاحة فوراً في جميع أدوات الاستيديو
