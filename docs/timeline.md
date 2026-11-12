# B5 — Timeline MVP: افتح، عدّل، احفظ، وأعِد الرندر بنفس البكسلات

B5 مش مخطط مشروع جديد ولا محرك رندر جديد. المشروع الموحّد و`history` و`store` و`snap` وpreview
المرجعي كانوا موجودين من المرحلة صفر/واحد؛ اللي كان ناقص هو **جلسة تحرير** تربطهم وتسدّ الحلقة:
`open → edit → save → reopen → render`.

> **الحالة (2026-11-12):** منفّذة — `tools/timeline_session.py` + 28 اختبارًا + معاينة قبل/بعد.
> الادّعاء الأساسي مُقاس: نفس المشروع، نفس الإطارات، بعد الحفظ وإعادة الفتح = **نفس sha256 للبكسلات**.

## 1. الشكل

```
project.json ──open──▶ Session ──apply(cmd)──▶ History ──▶ save ──▶ project.json'
                          │                     (undo/redo)
                          └──render(frame)──▶ unified_reference_preview ──▶ PNG + pixelSha256
```

| المكوّن | الدور في B5 |
|---|---|
| `unified_project_edit` | `split` · `trim` · `move` · `ripple` (منطق نقي موجود) |
| `unified_project_time` | `snap` (عتبة + لعب دور الاستعلام فقط) |
| `unified_project_history` | undo/redo بلقطات كاملة |
| `unified_project_store` | حفظ ذري مع `expected_revision` |
| `unified_reference_preview` | إطار RGBA من المشروع |
| `unified_render_graph` | `graphDigest` كهوية للخطة |

`timeline_session.py` هو الطبقة الجديدة الوحيدة: يترجم أوامر مكتوبة إلى تلك الوظائف، ويحوّل أخطاءها
إلى أكواد ثابتة.

## 2. لغة الأوامر

```json
{"commands": [
  {"op": "trim",   "clip": "c1", "start": 0, "end": 400000},
  {"op": "ripple", "start": 400000, "end": 480000, "tracks": ["v1"]},
  {"op": "split",  "clip": "c2", "at": 520000, "id": "c2b"},
  {"op": "move",   "clip": "c2b", "track": "v2", "start": 520000},
  {"op": "snap",   "tick": 516000, "tolerance": 8000},
  {"op": "undo"},
  {"op": "redo"}
], "frames": [0, 30, 70, 80, 110]}
```

- كل الأزمنة **ticks** صحيحة (هنا `timebase = 240000`، و`frameTicks = 8000` عند 30fps).
- `snap` استعلام: يرجّع التكّة المستهدفة ولا يغيّر شيئًا.
- أي أمر فاشل **لا يترك أثرًا**: المشروع والتاريخ كما كانا، والـCLI ما بيكتبش ملف خرج.

| الكود | المعنى |
|---|---|
| `T01` | أمر غير معروف، أو ليس كائنًا |
| `T02` | حقل ناقص/زائد |
| `T03` | قيمة مرفوضة من طبقة التحرير (خارج المدى، حدود، مسار…) |
| `T04` | لا يوجد ما يمكن التراجع عنه أو إعادته |
| `T05` | الحفظ مرفوض (تعارض إصدار، مسار موجود، ملف اتغيّر) |
| `T06` | تصدير EDL مرفوض — الرسالة بتحمل كود `E…` من [`edl.md`](edl.md) |
| `V01`–`V04` | إطار خارج المشروع، أو وسائط غير مدعومة في المعاينة المرجعية |

## 3. الحفظ والتعارض

- `save(path)` يحمل `expected_revision` (sha256 لبايتات الملف كما تُقرأ).
- لو الملف اتغيّر تحت إيديك → `T05` ولا كتابة.
- الحفظ لمسار **جديد** يكون إنشاءً أولًا (يفشل لو الملف موجود — لازم تفتحه الأول).
- `--autosave` يحفظ بعد كل أمر (نفس الإصدار المتحدّث)، والمنطق نفسه متاح `session.save(autosave=True)`.
- **التاريخ لا يُحفظ في الملف**: إعادة الفتح تبدأ جلسة نظيفة (`canUndo=false`). ده سلوك مقصود ومُختبر.

## 4. الهوية: «نفس الناتج» يعني إيه

- `pixelSha256` = بصمة خام RGBA8 للإطار — **هوية المحتوى**.
- `fileSha256` = بصمة ملف PNG (تعتمد على مُرمِّز Pillow؛ مذكورة للفحص لا للعقد).
- `graphDigest` = sha256 لخطة الرندر القياسية — يتغيّر مع أي تعديل ويرجع مع `undo`.

القياس في الاختبارات:
```
render(3) مرتين            → نفس pixelSha256 ونفس fileSha256
حفظ → إعادة فتح → render  → نفس pixelSha256 لكل الإطارات المطلوبة
تشغيل CLI مرتين من نفس المدخل → نفس ملف المشروع بايتًا ونفس بصمات الإطارات
```

## 5. مثال مقاس (ديمو 4 ثوانٍ، 360×640، 30fps، 120 إطارًا)

| الأمر | النتيجة |
|---|---|
| `trim c1 → 0..400000` | أول لقطة 3.33s بدل 4s |
| `ripple 400000..480000 v1` | c2 وc3 اتزحزحوا 80k tick لليسار — الفراغ اتقفل |
| `split c2 at 520000 → c2b` | c2 بقيت 120k، وc2b 120k |
| `move c2b → v2` | c2b خرجت من المسار المفكوك، فبقى فراغ 52.0–64.0s |
| `undo` ثم `redo` | رجوع كامل ثم إعادة — بنفس `graphDigest` |

```
before: f0=A f30=A f70=B f80=B f110=A
after : f0=A f30=A f70=فراغ f80=A f110=فراغ
graphDigest بعد الحفظ: 18386dfaef66…
```

## 6. الاستخدام

```bash
python3 tools/timeline_session.py check  project.json
python3 tools/timeline_session.py status project.json
python3 tools/timeline_session.py frame  project.json 80 -o out/f80.png
python3 tools/timeline_session.py script project.json edit.json -o out/edited.json --out-dir out/frames
python3 tools/timeline_session.py script project.json edit.json -o out/edited.json --autosave
python3 tools/timeline_session.py export project.json -o out/reel.edl      # تسليم EDL
python3 tools/timeline_session.py script project.json edit.json -o out/edited.json --edl out/reel.edl
```

`script` بيكتب الملف الناتج + `edited.frames.json` (لكل إطار: tick، pixelSha256، fileSha256، والملف)،
و`--edl` بيطلّع ملف التسليم بعد الحفظ مباشرةً — الـEDL بيتقرأ من نفس المشروع الناتج، مش من قائمة منسوخة.
`export` بيكتب `<out>.edl` + حزمته `<out>.edl.json`.
الخروج: `0` تمام · `1` أمر/رندر/EDL مرفوض (ولا يُكتب خرج) · `2` مشروع أو سكربت غير مقروء.

## 7. ما لا تدّعيه B5

- **مفيش واجهة رسومية**: المحرر المرئي (Media Bin · Timeline · Inspector) ما زال خارج النطاق؛
  B5 هي النواة القابلة للقيادة بأوامر، والـUI طبقة عليها لاحقًا.
- **مفيش تصدير فيديو**: العرض من المعاينة المرجعية (صور ثابتة P6)؛ الفيديو الحقيقي يبقى للـadapters.
- المعاينة المرجعية تقبل **صورة واحدة مفعّلة على مسار واحد**؛ أي شيء آخر يُرفض بـ`V02` بدل تخمين.
- التاريخ في الذاكرة فقط، وحدّه 100 خطوة، ولا يوجد تعاون متعدد الكتاب.
- الأزمنة ticks صحيحة ولا تقبل كسورًا؛ الـsnap يعمل على نفس الشبكة.

## 8. الخطوة التالية

**B6 ✅ منفّذ** — انظر [`profiles.md`](profiles.md) و[`subtitles.md`](subtitles.md)، والتسليم صار
[`edl.md`](edl.md) (CMX3600 من نفس المشروع الذي تعدّله هذه الجلسة). الخريطة مغلقة وقرارات المالك حُسمت
(60fps تجريبي · EDL · هوية واحدة)؛ المتبقي تنفيذًا: ربط البروفايل بمحرّك P عبر adapter، وأمر `--edl`
داخل الجلسة.
