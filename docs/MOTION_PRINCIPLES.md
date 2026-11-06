# مبادئ تصميم الحركة — Motion Design Principles

مستوحاة من [LottieFiles Motion Design Skill](https://github.com/LottieFiles/motion-design-skill)

---

## 🎬 الأعمدة الثلاثة

### 1. الغرض (Purpose)
كل حركة تخدم هدفاً: توجيه الانتباه، تأكيد الإجراء، أو خلق تسلسل.

### 2. الشخصية (Personality)
الحركة تعكس هوية العلامة التجارية.

### 3. الإتقان (Craft)
التفاصيل الدقيقة تصنع الفرق.

---

## 🏰 مبادئ ديزني الـ 12 (مكيفة للواجهات)

| # | المبدأ | التطبيق في UI |
|---|--------|---------------|
| 1 | **Squash & Stretch** | الأزرار تنضغط عند الضغط (scale 0.92) |
| 2 | **Anticipation** | حركة صغيرة للخلف قبل القفز (backOut) |
| 3 | **Staging** | العنصر المهم يتحرك أولاً |
| 4 | **Straight Ahead & Pose to Pose** | keyframes واضحة للحركات المعقدة |
| 5 | **Follow Through** | العناصر تستمر بالحركة بعد التوقف |
| 6 | **Slow In & Slow Out** | easing في البداية والنهاية |
| 7 | **Arcs** | الحركات تتبع منحنيات طبيعية |
| 8 | **Secondary Action** | حركة داعمة تضيف ثراءً |
| 9 | **Timing** | 200-300ms للمعظم، 400-500ms للأهم |
| 10 | **Exaggeration** | مبالغة خفيفة لجعل الحركة واضحة |
| 11 | **Solid Drawing** | تصميم متسق في كل الحالات |
| 12 | **Appeal** | حركة جذابة وممتعة |

---

## 🎭 شخصيات الحركة (Archetypes)

### 1. **المرح** (Playful)
- **Easing:** backOut, elasticOut
- **Duration:** 400-600ms
- **Use:** تطبيقات الأطفال، الألعاب، العلامات المرحة

### 2. **الأنيق** (Elegant)
- **Easing:** cubicOut, expoOut
- **Duration:** 500-800ms
- **Use:** الفخامة، الموضة، العقارات

### 3. **الكفء** (Efficient)
- **Easing:** cubicInOut, quadOut
- **Duration:** 150-250ms
- **Use:** الإنتاجية، الأعمال، الأدوات

### 4. **الحيوي** (Energetic)
- **Easing:** backOut, bounceOut
- **Duration:** 200-350ms
- **Use:** الرياضة، اللياقة، الشباب

---

## ⏱️ جداول التوقيت

### حسب الحجم

| الحجم | المدة | Easing |
|-------|-------|--------|
| **صغير** (< 100px) | 150-250ms | easeOut |
| **متوسط** (100-300px) | 250-400ms | easeInOut |
| **كبير** (> 300px) | 400-600ms | easeIn |

### حسب الأهمية

| الأهمية | المدة | Easing |
|---------|-------|--------|
| **عادي** | 200-300ms | ease |
| **مهم** | 300-450ms | easeInOut |
| **حاسم** | 400-600ms | spring |

### حسب المسافة

| المسافة | المدة | Easing |
|---------|-------|--------|
| **قصيرة** (< 20%) | 150-250ms | easeOut |
| **متوسطة** (20-50%) | 250-400ms | easeInOut |
| **طويلة** (> 50%) | 400-600ms | easeIn |

---

## 🎨 خرائط العاطفة → حركة

| العاطفة | الحركة | Easing | Duration |
|---------|--------|--------|----------|
| **فرح** | ارتداد عالي | backOut | 400ms |
| **هدوء** | تدفق ناعم | sineInOut | 600ms |
| **إثارة** | ارتداد سريع | elasticOut | 300ms |
| **ثقة** | حركة ثابتة | cubicOut | 350ms |
| **فضول** | ميلان خفيف | easeOutBack | 450ms |
| **احتراف** | حركة دقيقة | easeOutQuad | 250ms |

---

## 🎪 الأنماط الجاهزة

### الدخول (Entrance)

#### Fade + Slide
```
opacity: 0 → 1
y: 20px → 0
duration: 300ms
easing: easeOut
```

#### Scale + Fade
```
scale: 0.8 → 1
opacity: 0 → 1
duration: 250ms
easing: backOut
```

#### Slide from Edge
```
x: -100% → 0
duration: 350ms
easing: cubicOut
```

### الخروج (Exit)

#### Fade + Slide Up
```
opacity: 1 → 0
y: 0 → -20px
duration: 200ms
easing: easeIn
```

#### Scale Down
```
scale: 1 → 0.8
opacity: 1 → 0
duration: 200ms
easing: cubicIn
```

### التغذية الراجعة (Feedback)

#### نجاح (Success)
```
scale: 1 → 1.2 → 1
color: → green
duration: 300ms
easing: backOut
```

#### خطأ (Error)
```
x: 0 → -10 → 10 → -10 → 0
duration: 300ms
easing: easeInOut
```

#### تحميل (Loading)
```
rotate: 0 → 360deg
duration: 1000ms
easing: linear
loop: infinite
```

### التحويلات (State Changes)

#### Hover
```
scale: 1 → 1.05
boxShadow: 0 → 10px
duration: 200ms
easing: easeOut
```

#### Toggle
```
translateX: 0 → 100%
backgroundColor: gray → blue
duration: 250ms
easing: cubicInOut
```

---

## 📋 قائمة الجودة

### ✅ قبل النشر

- [ ] كل حركة لها غرض واضح
- [ ] التوقيت متناسق (200-400ms)
- [ ] easing مناسب للحركة
- [ ] لا يوجد اهتزاز أو ارتجاج غير مقصود
- [ ] الأداء سلس (60fps)
- [ ] يعمل على الأجهزة الضعيفة
- [ ] يحترم prefers-reduced-motion

### ❌ الأخطاء الشائعة

- ** Oscillation:** عنصر يهتز بلا نهاية
- ** Conflicting motions:** عناصر تتحرك في اتجاهات متعارضة
- ** Slow feedback:** تأخير > 100ms في الاستجابة
- ** Unnecessary motion:** حركة بلا غرض
- ** Inconsistent timing:** توقيتات مختلفة لنفس النوع

---

## 🔧 حل المشاكل

### الحركة بطيئة
- قلل المدة لـ 200-300ms
- استخدم easeOut بدلاً من easeInOut
- قلل المسافة

### الحركة سريعة جداً
- زد المدة لـ 400-500ms
- أضف anticipation
- استخدم easeIn للحركات الطويلة

### الحركة غير طبيعية
- أضف easing (ليس linear)
- أضف anticipation
- أضف follow-through

### اهتزاز في النهاية
- تحقق من قيم النهاية
- استخدم easeOut قوي
- أضف damping

---

## 📚 المراجع الكاملة

الملفات الكاملة في `docs/motion-principles/`:

```
docs/motion-principles/
├── SKILL.md                          # المرجع السريع
├── director/
│   ├── core-philosophy.md            # الأعمدة الثلاثة
│   ├── decision-framework.md         # إطار القرار
│   ├── disney-principles.md          # 12 مبدأ ديزني
│   ├── motion-personality.md         # 4 شخصيات
│   ├── emotion-mapping.md            # عاطفة → حركة
│   ├── choreography.md              # التنسيق
│   ├── narrative-structure.md        # السرد
│   └── context-adaptation.md         # التكيف
├── patterns/
│   ├── entrance-exit.md              # دخول/خروج
│   ├── state-feedback.md             # تغذية راجعة
│   ├── ambient-continuous.md         # مستمر
│   └── multi-element.md              # متعدد العناصر
└── reference/
    ├── timing-easing-tables.md       # جداول
    ├── property-selection.md         # اختيار الخصائص
    ├── quality-checklist.md          # قائمة الجودة
    └── troubleshooting.md            # حل المشاكل
```

---

**المصدر:** [LottieFiles Motion Design Skill](https://github.com/LottieFiles/motion-design-skill) — MIT License
