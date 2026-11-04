# Slide Wall — مثال كامل P / K / R

مثال صامت مدته **6 ثوانٍ / 30 fps / 1080×1920**، بأرقام `01..04` فقط وبلا logo أو branding افتراضي أو محتوى factual. الملفات هنا overlays للقالب، وليست مشروع فيديو مؤرشفًا داخل Git؛ أداة الإنشاء تنسخها إلى مشروع حقيقي كامل بالخطوط والأصول وentrypoints الحالية.

## المسار الزمني

| الزمن | Slide Wall | Fixed Stage |
|---|---|---|
| `0.0–0.8` | overview لأربع شرائح | fullscreen ثم بداية framing عند 0.6 |
| `0.8–1.8` | approach إلى `slide-01` | framed منذ 1.0 |
| `1.8–2.8` | hold مقروء على `01` | framed |
| `2.8–3.8` | انتقال `01 → 02` | framed |
| `3.8–4.8` | hold مقروء على `02` | framed |
| `4.8–6.0` | return إلى overview | framed ثم fullscreen |

الشريحة `3×4` والنافذة `900×1200` لهما aspect ratio واحد؛ لذلك يطابق الوجه الأمامي `win(t)` أثناء hold ويمكن استخدام نفس محتواها لأول فريم في match cut. الشريحة `02` تبدأ بـrotation حقيقي `[0.06,-0.18,0.04]` لاختبار projection غير المحاذي، ثم تحاذي الكاميرا basis الخاصة بها أثناء hold.

## إنشاء مشروع حقيقي

من جذر المستودع، وبعد `tools/setup.sh`:

```bash
python3 tools/new_slide_wall_example.py wall-p --engine p --out /absolute/work/wall-p
python3 tools/new_slide_wall_example.py wall-k --engine k --out /absolute/work/wall-k
python3 tools/new_slide_wall_example.py wall-r --engine r --out /absolute/work/wall-r
```

استخدم مسارًا خارج Git. `--force` يعيد نسخ overlays مثل `tools/new_project.py`؛ لا يحذف أعمالًا أخرى تلقائيًا.

## رندر P

```bash
python3 tools/render_p_segment.py \
  --project /absolute/work/wall-p --from-frame 0 --to-frame 180 \
  --out /absolute/work/wall-p/out/wall.mp4 --ffmpeg "$(command -v ffmpeg)"
```

## رندر K

```bash
cd /absolute/work/wall-k
node src/render.js --from 0 --to 6 --fps 30 --out renders/preview --name "Slide Wall"
# أو frames وlayout/replay audit:
node src/render.js --from 0 --to 6 --fps 30 --jpg --out cache/frames
node src/render.js --from 0 --to 6 --fps 30 --audit --replay --every 15 --out cache/audit
```

## رندر R

```bash
cd /absolute/work/wall-r
npm ci
node node_modules/typescript/bin/tsc --noEmit
node scripts/launch-remotion.mjs render src/index.ts SlideWallExample out/wall.mp4
```

## ملاحظات الإنتاج

- هذا preview صامت ولا يدّعي وجود VO. لا تنسخ مدته إلى reel حقيقي: اشتق `plan/beats.json` من VO مقاس، واضبط نهاية `slide-wall.json` على المدة نفسها.
- `stage.json` في المثال `autoWrap=false` لأن كل engine يستدعي Fixed Stage يدويًا ويمرر `state.win` للـwall. لا تنشئ Stage ثانيًا.
- P/K يستخدمان `draw_directed_text` / `drawDirectedText` ويمرران conservative number rect لتسجيل النص المسقوف في layout audit. R يستخدم `<DirectedText>` داخل DOM الفعلي.
- `supportsReducedMotion=true` و`SUPPORTS_REDUCED_MOTION=True` موجودان لأن reduced mode محقق كقطع إلى endpoint، لا كتجاهل للمعلومة.
- اقرأ العقد والقيود في `docs/slide-wall.md` قبل استبدال الأرقام بمحتوى فعلي.
