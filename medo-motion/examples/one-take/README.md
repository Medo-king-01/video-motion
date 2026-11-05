# One-Take — مثال Today كامل P / K / R

مثال أصلي صامت مدته **8 ثوانٍ / 30 fps / 1080×1920** لواجهة مهام بسيطة. لا يستخدم VO أو logo أو network asset أو ادعاءً factual. الملفات overlays للقالب؛ أداة الإنشاء تنسخها إلى مشروع حقيقي كامل بالخطوط وentrypoints الحالية.

## الحالات الدلالية

| الوقت | الحالة | التغيير |
|---|---|---|
| `0.0` | opening | Today وبطاقتان وزر Start focus |
| `1.2` | interface | اكتمال المهمة الأولى واستقرار الواجهة |
| `2.4` | interaction | الكاميرا تقترب من الزر والـcursor ينقر |
| `3.6` | selected | بطاقة Focus تتكبر وتحمل علامة الإكمال الثانية |
| `4.8` | feature | Focus mode وNotifications paused يظهران باستمرار |
| `6.0` | progress | `2 of 3 complete` وامتلاد شريط التقدم |
| `7.2` | result | النتيجة `3` وDay complete |
| `8.0` | final | إعادة framing نهائية دون cut أو scene fade |

النقرتان عند `2.15s` و`3.25s`، ومسار cursor والكاميرا والعناصر كلها absolute-time وقابلة للتقييم بأي ترتيب. أرقام الإكمال مستخدمة بدل checkmark لضمان تغطية Cairo نفسها في P/K/R.

## إنشاء مشروع حقيقي

من جذر المستودع بعد `tools/setup.sh`:

```bash
python3 tools/new_one_take_example.py take-p --engine p --out /absolute/work/take-p
python3 tools/new_one_take_example.py take-k --engine k --out /absolute/work/take-k
python3 tools/new_one_take_example.py take-r --engine r --out /absolute/work/take-r
```

استخدم مسارًا خارج Git. `--force` يعيد كتابة overlays ولا يعمل كدمج أو backup.

## الرندر

يفحص `reel_lint` العقد بـ`O00/O01`، وتفحصه K/R launchers قبل الرندر. الفحص العام للـreel يحتاج أيضًا visual-direction وتوقيتات VO مقاسة؛ لا يختلق هذا المثال الصامت word anchors.

**P — كامل المثال أو ثلاثة فريمات للاختبار:**

```bash
python3 tools/render_p_segment.py \
  --project /absolute/work/take-p --from-frame 0 --to-frame 240 \
  --out /absolute/work/take-p/out/take.mp4 --ffmpeg "$(command -v ffmpeg)"
# Short smoke: --from-frame 60 --to-frame 63
```

**K:**

```bash
cd /absolute/work/take-k
node src/render.js --from 0 --to 8 --fps 30 --out renders/preview --name "One Take"
# Short representative frames:
node src/render.js --from 3.2 --to 3.3 --fps 30 --jpg --out cache/frames
```

**R:**

```bash
cd /absolute/work/take-r
npm ci
node node_modules/typescript/bin/tsc --noEmit
node scripts/launch-remotion.mjs render src/index.ts OneTakeExample out/take.mp4
# Repeatable representative still:
node scripts/launch-remotion.mjs still src/index.ts OneTakeExample cache/frame.png --frame=97
```

## ملاحظات الإنتاج

- `copy.json` فارغ عمدًا لأن المثال صامت؛ UI labels تعيش مع عناصرها في `one-take.json`. في reel حقيقي اشتق `beats.json` من VO مقاس، واضبط `duration` ونهاية states/cursor على المدة نفسها.
- `supportsReducedMotion=true` و`SUPPORTS_REDUCED_MOTION=True` معلنان لأن reduced mode ينتقل إلى target state ويثبت cursor بلا ring.
- P/K يرسمان directed text في cached faces ويسجلان conservative transformed boxes؛ R يستخدم DOM `DirectedText`. لا تتوقع pixel equality بين rasterizers.
- المثال fullscreen. عند دمجه في Fixed Stage مرّر `stageState.win` كـviewport بدل إنشاء Stage ثانٍ.
- اقرأ `docs/one-take.md` للعقد الكامل والقيود وأوامر الاختبار.
