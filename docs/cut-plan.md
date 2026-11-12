# B4 — استيعاب فيديو و`cut-plan.json` قابل للمراجعة

B4 بتاخد ملف فيديو، تقراه **مرة واحدة**، وتطلّع تقرير وسائط حتمي، ثم خطة قطع مكتوبة يقدر المالك
يقراها ويعدّلها. **مفيش تنفيذ:** لا قص، لا إعادة ترميز، لا تصدير. المحرك بيقترح، والإنسان بيقرر.

> **الحالة (2026-11-12):** منفّذة — `video_ingest.py` + `cut_plan.py` + schema + معاينة + **50 اختبارًا**
> (15 للاستيعاب، 35 للخطة). القرار الأخير مكتوب في `docs/exploitation-map.md` (B4 ✅).

## 1. المسار

```
clip.mp4 ──video_ingest.py──▶ media-report.json ──cut_plan.py build──▶ cut-plan.json
                                                                        │
                                          review / set / preview ◀─────┘
                                                                        │
                                                     (B5) timeline ──────┘   ← لا يوجد منفّذ في B4
```

| الملف | الدور |
|---|---|
| `tools/video_ingest.py` | يقرأ الفيديو بـPyAV ويطلّع `media-report.json` |
| `tools/cut_plan.py` | يبني الخطة، يتحقّق منها، يطبعها، يعدّلها، يرسمها، ويصدّر **EDL** للقطع المحفوظة، ويرفض التنفيذ |
| `medo-motion/schema/cut-plan.schema.json` | مرجع بنيوي للخطة (المنطق الدلالي في `validate()`) |
| `tests/test_video_ingest.py` · `tests/test_cut_plan.py` | 15 + 35 اختبارًا |

## 2. تقرير الوسائط

```json
{
  "version": 1,
  "source": { "name": "clip.mp4", "sha256": "…", "bytes": 251903 },
  "video": { "width": 480, "height": 270, "fps": 30.0, "duration": 6.0,
             "frames": 180, "vfr": false, "codec": "mpeg4", "container": "mov,mp4,…" },
  "sampling": { "grid": [16, 9], "decoded": 180, "step": 1, "maxFrames": 7200 },
  "deltas": [0.0, 0.412, …]
}
```

- **البصمة** `sha256` مربوطة بالملف نفسه: لو الفيديو اتغيّر، الخطة القديمة ما بتنفعش.
- **`deltas`** = طول `frames - 1`، كل قيمة متوسط الفرق المطلق بين شبكتين **16×9 RGB**.
  الشبكة ألوان مش luma، لأن قطع أخضر→أحمر ما يبانش في الإضاءة وحدها (ده كان عيبًا اتصلّح في B4).
- **`vfr`** = انحراف زمني: أي إطار يبعد عن `1/fps` بأكثر من 5%، ولو النسبة فوق 2% نعلن VFR.
- **السقف** 7200 إطار (4 دقائق @30fps) و`--max-frames` يعدّله؛ فوقه رسالة صريحة، لا صمت.
- كل التقريب 3 خانات (`delta`) و4 (`pts`)، فالتشغيل التاني على نفس الملف = نفس JSON بايتًا.

## 3. من الأرقام إلى اللقطات

```
boundary عند الإطار i+1  لو  deltas[i] ≥ threshold
shots = [0..b1, b1..b2, …, bk..frames]
merge  لو  طول اللقطة < minShot  → تُضَمّ للي قبلها ويختفي الحد
```

- الافتراضيات: `threshold = 25` من 255، `minShot = 0.4s`.
- الحركة العادية بتبقى عادة تحت 1–2، والقطع الحقيقي فوق 40 — الفصل واسع مش حساس.
- اللقطة الأولى `reason = "first-shot"`، والبقية `"visual-cut"` مع `score` = قيمة الـdelta.
- آخر لقطة تنتهي عند `source.duration` بالظبط (مش `frames/fps` المستدير).

## 4. عقد الخطة وأكواد الرفض

```json
{
  "version": 1,
  "source": { "sha256": "…", "duration": 6.0, "fps": 30.0 },
  "video": { "width": 480, "height": 270, "fps": 30.0, "duration": 6.0, "frames": 180, "vfr": false },
  "settings": { "threshold": 25.0, "minShot": 0.4 },
  "cuts": [
    { "id": "cut-01", "in": 0.0, "out": 1.5, "keep": true, "reason": "first-shot", "score": 0.0 }
  ],
  "totals": { "shots": 4, "keptSeconds": 4.5, "rejectedSeconds": 1.5, "duration": 6.0 }
}
```

| الكود | يرفض |
|---|---|
| `C00` | إصدار غير 1، `source` ناقص/بصمة مش 64 hex، `duration/fps ≤ 0`، تعارض `video.duration` |
| `C01` | حقل مجهول أو ناقص على أي مستوى، `vfr` مش boolean |
| `C02` | `cuts` فاضية أو مكرّرة أو مش مرتّبة أو فيها فراغ/تراكب، آخر قطع ما ينتهيش عند المدة |
| `C03` | `in < 0` أو `out ≤ in` أو `out` بعد المدة أو `score` سالب أو أقصر من `minShot` |
| `C04` | `keep` مش boolean |
| `C05` | `threshold` خارج (0,255] أو `minShot` سالب |
| `C06` | `totals` ما تطابقش إعادة الحساب من `cuts` |

`totals` مش زينة: أي تعديل بيإعادة حسابه، وأي خطة بتقول رقمًا غير اللي في `cuts` بترجع `C06`.

## 5. الاستخدام

```bash
python3 tools/video_ingest.py clip.mp4 -o out/media-report.json
python3 tools/cut_plan.py build out/media-report.json -o out/cut-plan.json
python3 tools/cut_plan.py review out/cut-plan.json
python3 tools/cut_plan.py set out/cut-plan.json cut-03=reject
python3 tools/cut_plan.py preview out/cut-plan.json -o out/cut-plan.html
python3 tools/cut_plan.py check out/cut-plan.json
python3 tools/cut_plan.py render …        # exit 3
```

الخروج: `0` تمام · `1` خطة/تقرير مرفوض · `2` ملف غير مقروء أو قيمة `set` غلط · `3` **تنفيذ مرفوض**.

## 6. مثال مقاس (6 ثوانٍ، 480×270، 30fps)

```
4 shots · keep 6.00s / 6.00s
cut-01  0.00–1.50  keep    first-shot   0.00
cut-02  1.50–3.50  keep    visual-cut  75.84
cut-03  3.50–5.00  keep    visual-cut  88.26
cut-04  5.00–6.00  keep    visual-cut  63.16

بعد  set cut-03=reject  →  keep 4.50s · reject 1.50s   (والمجموع يفضل 6.00s)
```

## 7. ما لا تدّعيه B4

- **مفيش تنفيذ**: `render` بيرجع `3` برسالة صريحة — الخطة تتسلّم لـB5.
- مفيش تحليل صوتي (صمت/نَفَس/موسيقى) ولا كلام: ده يحتاج مسار صوت منفصل.
- مفيش تعرّف على وجوه أو محتوى أو مشاهد دلالية، ومفيش AI في أي قرار.
- VFR يُكتشف من الطوابع الزمنية، لكن إعادة التوقيت نفسها مش في B4.
- سقف 7200 إطار مقصود: أداة مراجعة، مش ingest لمادة طويلة.
- الـpreview رسم SVG للخطة، مش صور مصغّرة من الفيديو.

## 8. الخطوة التالية

**B5 مكتملة** ([`timeline.md`](timeline.md)): جلسة تحرير تفتح المشروع وتعدّله وتحفظه وتعيد رندره بنفس البكسلات.
**B6 ✅ منفّذ** — [`profiles.md`](profiles.md) (البروفايلات الأربعة، رفض 60fps بلا موافقة) و
[`subtitles.md`](subtitles.md) (SRT/VTT من نفس `copy.json`). الخريطة مغلقة؛ `render` في خطة القطع
يبقى مرفوضًا بـexit 3 كما هو.
