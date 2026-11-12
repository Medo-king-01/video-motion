# المحرر المحلي: أول واجهة مرئية فوق النواة

**الحالة:** منفّذ (2026-11-12) · **الكود:** `tools/editor_server.py` + `editor/index.html`
**الاختبارات:** `tests/test_editor_server.py` (9)

البند الرابع في [`development-plan-status.md`](development-plan-status.md) §3 كان «المحرر المرئي». النواة
(split/trim/move/ripple/snap/undo/حفظ ذري) كانت جاهزة ومجرّبة من الـCLI، والناقص كان الواجهة. الصفحة دي
هي الطبقة الأولى: **بيانات حقيقية، عمليات حقيقية، نفس الدوال** — مش نموذج بالورق.

## 1. التشغيل

```bash
python3 tools/editor_server.py projects/demo/project.json --port 8777
# ثم افتح http://127.0.0.1:8777
```

- بيربط على `127.0.0.1` افتراضيًا لأنه **بلا مصادقة**. `--host 0.0.0.0` للـpreview proxy فقط، ومع
  شبكة موثوقة.
- الصفحة ملف واحد بلا npm ولا CDN: HTML + JS عادي، فتعمل offline وبتفتح في iframe.

## 2. إيه اللي بيشتغل في الواجهة

| العنصر | السلوك | الدالة اللي تحته |
|---|---|---|
| Timeline متعدد المسارات | كل مقطع بلوك بموضعه وطوله، والانتقالات علامة على القطع، ورأس تشغيل متحرك | `project.tracks` |
| Preview | إطار PNG من نفس `render_frame` اللي التصدير بيستخدمه | `unified_reference_preview` |
| تشغيل/إيقاف | يقدّم الإطارات بمعدل المشروع | `frameTicks` |
| Split / Trim / Ripple | على المقطع المختار، ويرفض أي عملية مش قانونية | `unified_project_edit` |
| Undo / Redo | تاريخ لقطات، وكل خطوة بتتسجل في الـautosave | `unified_project_history` |
| Captions | تحرير نص/حجم/لون/محاذاة العربية مباشرة | `texts[]` في العقد 1.3 |
| Export | MP4 بـH.264 من إطارات P + WAV مقيس لو فيه صوت | `video_export` + `adapter_p` |
| Capabilities | شريط أحمر بأسباب رفض P للمشروع قبل أي رسم | `adapter_p.preflight` |
| Autosave | يُكتب على كل عملية، ويُمسح بعد حفظ ناجح | `unified_project_store` |

## 3. الـAPI (كله JSON)

| المسار | المعنى |
|---|---|
| `GET /api/project` | المشروع + `revision` + حالة undo/redo + وجود autosave وقدّ إيه |
| `POST /api/op` | `split` · `trim` · `move` · `ripple` · `caption` · `undo` · `redo` |
| `POST /api/save` | حفظ بإصدار مطابق ثم مسح المسودة |
| `GET /api/frame?index=N` | PNG لإطار واحد |
| `GET /api/capabilities` | قدرات P + نتيجة `preflight` للمشروع الحالي |
| `POST /api/export` | تصدير MP4 ويرجّع البايتات والبصمة |
| `GET/POST /api/recover` | عرض المسودة / `apply` أو `discard` |

## 4. معالجة الرفض

كل عملية بتمر على دوال النواة، فأي مخالفة (قص عند صفر، trim خارج المقطع، نص مش موجود) بترجع
**HTTP 400 برسالة النواة نفسها**، والصفحة بتعرضها في شريط أحمر وتكتبها في السجل — بدل ما تسكت أو
تحفظ حالة نص-صحيحة.

## 5. حدود ما يُدّعى

- **مفيش حذف مسار، ولا إضافة وسائط من الواجهة** بعد (الوسائط من `tools/workflows.py` أو JSON).
- **مفيش keyframes في الواجهة**؛ الـInspector بيحرّر النص والاختيار فقط.
- **مفيش تعاون متعدد المستخدمين**: الجلسة في الذاكرة، والقفل التعاوني في `store` هو كل ما فيه.
- **مفيش مصادقة ولا HTTPS** (محلي فقط)، ولا شبكة أثناء الرندر.
- **مفيش drag-and-drop**؛ الحركة عبر حقول وأزرار صريحة، لأن السحب أسهل في إنه يغلط بصمت.
