# انتقالات GLSL — GPU Transitions

**١٨٩ انتقال** مدعوم بالمعالج الرسومي (GPU) من [gl-transitions.com](https://gl-transitions.com).

---

## 🎬 الأنواع

### 📦 أشكال هندسية

| الانتقال | الوصف | المعاملات |
|----------|-------|-----------|
| **Accordion** | طي أكورديون | pleats, direction, shading, perspective |
| **ArrowWipe** | مسح بشكل سهم | — |
| **BandWipe** | مسح بأشرطة | — |
| **BowTie** | عقدة فراشة | — |
| **BowTieHorizontal** | عقدة فراشة أفقية | — |
| **CircleIris** | دائرة قزحية | angle, center |
| **CircleOpen** | دائرة تفتح | opening, center |
| **ClockWipe** | مسح عقارب الساعة | — |
| **Cube** | مكعب ثلاثي الأبعاد | persp, oxyz, unzoom |
| **DirectionalWipe** | مسح اتجاهي | direction, smoothness |

### 🌊 تأثيرات سائلة

| الانتقال | الوصف | المعاملات |
|----------|-------|-----------|
| **ButterflyWave** | موجة فراشة | amplitude, waves, color |
| **Dreamy** | حلمي ضبابي | — |
| **GlitchDisplace** | خلل مزاح | strength |
| **LinearBlur** | ضبابية خطية | — |
| **Morph** | تحول شكل | strength |
| **Ripple** | تموج | amplitude, smoothness, center |
| **WaterDrop** | قطرة ماء | amplitude, size, iterations |
| **Wave** | موجة | amplitude, frequency |
| **Wind** | رياح | size |

### 💥 تأثيرات انفجارية

| الانتقال | الوصف | المعاملات |
|----------|-------|-----------|
| **BloomDissolve** | ذوبان متوهج | — |
| **BokehDissolve** | ذوبان بوكيه | — |
| **BurnThrough** | حرق | color |
| **CellDissolve** | ذوبان خلايا | — |
| **ColorPhase** | تحول ألوان | — |
| **DoomScreen** | شاشة دوم | amplitude, noise |
| **Flash** | وميض | color, intensity |
| **RadialBlur** | ضبابية شعاعية | — |
| **Spiral** | حلزوني | — |
| **Swirl** | دوامة | — |

### 🚀 حركات ديناميكية

| الانتقال | الوصف | المعاملات |
|----------|-------|-----------|
| **CameraShake** | اهتزاز كاميرا | — |
| **CrossZoom** | زوم متقاطع | strength |
| **Fade** | تلاشي | — |
| **FadeColor** | تلاشي لوني | colorA, colorB, colorPhase |
| **Flip** | قلب | direction, axis |
| **Push** | دفع | direction |
| **Slide** | انزلاق | direction |
| **SquareSwizzle** | مربعات متبادلة | — |
| **Stretch** | تمدد | — |
| **Swap** | تبديل | direction |

### 🎨 تأثيرات فنية

| الانتقال | الوصف | المعاملات |
|----------|-------|-----------|
| **Ascii** | ASCII art | — |
| **BlockCover** | تغطية بمربعات | — |
| **BlockSlide** | انزلاق مربعات | — |
| **BrushWipe** | مسح بفرشاة | — |
| **Chessboard** | رقعة شطرنج | — |
| **Comb** | مشط | — |
| **CrazyParametricFun** | بارامتري مجنون | — |
| **Dissolve** | ذوبان | — |
| **Perlin** | ضوضاء بيرلين | — |
| **SquaresWire** | أسلاك مربعات | — |

### 📐 انتقالات متقدمة

| الانتقال | الوصف | المعاملات |
|----------|-------|-----------|
| **CrossWarp** | تشويه متقاطع | — |
| **DirectionalWarp** | تشويه اتجاهي | — |
| **KaleidoScope** | مشكال | speed, angle |
| **MultiPageWipe** | مسح متعدد الصفحات | — |
| **Pixelize** | بكسلة | — |
| **PolarFunction** | دالة قطبية | segments |
| **Squeeze** | ضغط | color |
| **TangentMotionBlur** | ضبابية حركة | — |
| **Wind** | رياح | size |
| **ZoomBlur** | ضبابية زوم | strength |

---

## 🔧 الاستخدام

### في المشروع

```json
{
  "transition": {
    "type": "gl-Cube",
    "duration": "0.8s",
    "params": {
      "persp": 2.0,
      "unzoom": 0.5
    }
  }
}
```

### في الكود

```python
# من assets/gl-transitions/
glsl_code = load_shader('Cube.glsl')
uniforms = {
    'persp': 2.0,
    'oxyz': [0, 0, 0.5],
    'unzoom': 0.5
}
```

---

## 📁 الملفات

```
assets/gl-transitions/
├── Accordion.glsl
├── ArrowWipe.glsl
├── BloomDissolve.glsl
├── CircleIris.glsl
├── Cube.glsl
├── Dreamy.glsl
├── Flash.glsl
├── GlitchDisplace.glsl
├── Morph.glsl
├── Ripple.glsl
├── ... (189 ملف)
└── README.md
```

---

## ⚠️ متطلبات

- **GPU** مدعوم (WebGL/WebGPU)
- **FFmpeg** مع دعم OpenGL (للرندر)
- عند عدم توفر GPU: fallback للانتقالات العادية

---

## 🎯 متى تستخدمها

### ✅ مناسب

- رندر على GPU متاح
- تريد تأثيرات معقدة (Bloom, Glitch, 3D)
- سرعة الرندر مهمة
- تأثيرات سائلة وعضوية

### ❌ غير مناسب

- رندر CPU فقط
- تحتاج توافق كامل
- تأثيرات بسيطة كافية

---

## 🔗 المصادر

- [gl-transitions.com](https://gl-transitions.com) — معرض تفاعلي
- [GitHub](https://github.com/gl-transitions/gl-transitions) — الكود المصدر
- **الرخصة:** MIT

---

**المجموع:** ١٨٩ انتقال GPU جاهز للاستخدام
