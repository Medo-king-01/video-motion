# الأيقونات المتحركة — من itshover للمحركين

## الخلاصة | Short answer
اللينك اللي بعته (`npx shadcn@latest add https://itshover.com/r/plug-connected-icon.json`) **ينفع** كنقطة بداية،
بس **مش بينفّذ جوه الساندبوكس**: `itshover.com` مش متاح من هنا (الطلب بيرجع فاضي)، ومفيش باكدج `itshover` على npm.
فبدل ما المشروع يستنى الإنترنت، عملنا **طبقة أيقونات متحركة أصلية** بنفس فكرة itshover (أيقونة stroke + أنيميشن عند الظهور)،
وبنفس الأسماء الشائعة، وبتشتغل **في المحركين** اللي بنصدّر بيهم الريلز:

| | استخدم إيه | فين |
|---|---|---|
| محرك K (Canvas/Playwright) | `drawIcon(ctx, 'cpu', t, {...})` | `templates/render/lib/icons.js` |
| محرك P (Pillow) | `draw_icon(fr, 'cpu', t, x, y, ...)` | `templates/procedural-reels/icons.py` |
| ويب / React | `svg/cpu.svg` + `.reel-icon` | `icons/svg/`, `icons/icon.css` |
| مكوّن itshover فعلًا | `npx shadcn@latest add …` | `icons/components.json` + `icons/examples/PlugConnectedIcon.jsx` |

## ليه مش ركّبنا itshover مباشرة؟ | Why not literally
1. **الشبكة:** التحقق من `https://itshover.com/r/plug-connected-icon.json` من الساندبوكس بيرجّع `000` (محجوب)، ومفيش نسخة على npm.
2. **الريفيرنس:** مكونات itshover بتُستهلك في ويدجت، والمحركين بتوعنا بيرسموا على **Canvas** أو **Pillow** — مش DOM. أي مكوّن React
   لازم يتحوّل لصور/مسارات قبل ما يدخل فريم.
3. **الألوان:** الهوية بتاعتنا 12 لون مقفولين، ومكونات جاهزة بتيجي بألوانها. عندنا اللون بيتحدد وقت الرسم → مستحيل تخرج برة البالِت.

فالطبقة اللي عندنا هي **العقد** نفسه: نفس الشبكة (24×24)، نفس الأنيميشن (رسم تدريجي + نبضة)، نفس الأسماء
(`plug-connected`, `cpu`, `battery` …). لما تشتغل على جهاز فيه إنترنت، تقدر تضيف مكون itshover وتنقل مساراته في
`medo-motion/icons/registry.json` وتعمل Rebuild — والمحركين ياخدوه فورًا.

## البنية | Layout
```
medo-motion/icons/
  registry.json     ← المصدر الوحيد (شكل + توقيت + اسم عربي)
  build.py          ← يولّد الـ SVG + المحركين + manifest (وفيه --check)
  svg/<id>.svg      ← 12 أيقونة متحركة (CSS داخل الـ SVG)
  icon.css          ← .reel-icon + مقاسات + سطح فاتح/غامق
  components.json   ← إعداد shadcn (registries["@itshover"])
  examples/         ← مكوّن React بأسلوب itshover
  manifest.json     ← فهرس
```
المولَّد: `templates/render/lib/icons.js` و`templates/procedural-reels/icons.py` (متعدّلهمش بإيدك).

## في الريل | Inside a reel
- أيقونة الشرح بتظهر مع الكلمة اللي بتقول اسمها (الكابشن)، وأنيميشن الرسم بيخلص قبل ما الكلمة تكمّل.
- المقاسات: 128px للمحتوى، 176px لما الأيقونة هي البطل، وممنوع أقل من 128px على موبايل.
- اللون: على الفاتح stroke = `ink` + أكسنت `red`؛ على الغامق stroke = `paper` + أكسنت `salmon`
  (**ممنوع** stroke أحمر على غامق — التباين 2.01:1).
- الأيقونة مش بديل عن الدايرة الحمرا الكبيرة: هي تفصيلة، مش بطل المشهد.
- الحركة بتتكرر مع كل مشهد جديد (`loop: false` للظهور مرة واحدة، `loop: true` للأيقونات الحيّة زي `wifi`).

## أوامر | Commands
```bash
python medo-motion/icons/build.py            # يبني الـ SVG + المحركين
python medo-motion/icons/build.py --check    # يتأكد إن المولَّد مطابق للـ registry (بيتشغّل في make ci)
python3 tools/icons_sheet.py                 # شيت مراجعة (المحرك P)
eval "$(node tools/chromium.mjs --env)" && node tools/icons_preview.mjs   # شيت مراجعة (المحرك K)
```

## إضافة من itshover (على جهاز فيه إنترنت)
```bash
# 1) في بروجكت React (مش لازم يكون نفس ريبو الفيديوهات)
cp <skill>/medo-motion/icons/components.json ./components.json
npx shadcn@latest add https://itshover.com/r/plug-connected-icon.json
#    أو عبر الـ alias بعد ما الـ registry يتقرأ:
npx shadcn@latest add @itshover/plug-connected-icon

# 2) انقل المسارات (d / rect / circle) للأيقونة في registry.json بنفس اسم itshover
# 3) python medo-motion/icons/build.py
```
راجع ترخيص الأيقونة قبل ما تثبّتها في الريبو. أي أيقونة مش واضح ترخيصها → ارسمها بنفسك على شبكة 24 (زي الـ 12 الحالية).

## حدود | Known limits
- مفيش cubic curves في الـ registry (polylines فقط) عشان نفس الشكل يترسم في Canvas وPillow وSVG بدون محرّك SVG.
  لو أيقونة itshover فيها منحنيات، اتبسّطها لـ polylines أو ضيف أنيميشن بس واستخدمها في الويب.
- الأنيميشن أنواعه 3 بس دلوقتي: draw (رسم تدريجي) + نبضة النقطة + ظهور التعبئة. أي أنيميشن تاني (spin/morph) محتاج بريميتيف جديد في `build.py`.
- SVG ملفات مستقلة: لازم inline عشان `currentColor` تشتغل؛ `<img src="…svg">` مش هياخد لون الصفحة.
