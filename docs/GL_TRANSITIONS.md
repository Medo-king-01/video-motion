# انتقالات GLSL — مخزن مرجعي

`assets/gl-transitions/` فيه **<!-- AUTO:gl_transitions -->189<!-- /AUTO --> ملف شيدور** (`*.glsl`) من مجموعة
[gl-transitions](https://github.com/gl-transitions/gl-transitions).

> **المخزن ده مش موصّل بمسار الرندر.** مفيش محرك (P ولا K ولا R) ولا أداة بتحمّل ملف `.glsl` أو
> بتشغّله: مفيش loader، ومفيش نوع انتقال اسمه `gl-…` في أي خطة، ومفيش مسار GPU للانتقالات.
> الملفات مرجع للأفكار والأسماء فقط.

## اللي بيشتغل فعلًا

الانتقالات المدعومة في الرندر هي **<!-- AUTO:transitions -->14<!-- /AUTO --> انتقال** متعرّفين في
`medo-motion/motion/transitions.json`، ومحسوبين vector/CPU بنفس الأرقام في المحركات — التفاصيل
والأسماء في [`docs/transitions.md`](transitions.md). لو عايز انتقال في ريل، اختاره من هناك.

## إيه اللي بيقرا المخزن

| القارئ | بيعمل إيه |
|---|---|
| `assets/techniques.json` | <!-- AUTO:techniques_glsl -->189<!-- /AUTO --> مدخل `source: "gl-transitions"` — بيانات وصفية بس (اسم، وصف، `glsl_file`، `uniforms`). وصف المدخل "GPU-accelerated transition" بيوصف الشيدور نفسه، مش حاجة الاستوديو بيرندرها. |
| `tests/test_techniques.py` | بيتأكد إن كل `glsl_file` بيشاور على ملف موجود. |
| `tools/sync_docs_numbers.py` | بيعدّ الملفات عشان الأرقام اللي في الوثائق. |
| `tools/gl_headers.py` | بيقرا رؤوس الملفات ويولّد جدول الرخص تحت. |
| `tools/dev/_archive/merge_gl_transitions.py` | سكربت الاستيراد الأصلي (أرشيف، مابيشتغلش). |

`tests/test_gl_transitions.py` بيفشل لو أي ملف في مسار الرندر بدأ يقرا المخزن — ساعتها الوثيقة دي
لازم تتحدّث.

## الرخص — غير محسوم

كل ملف بيعلن رخصته في رأسه، والمخزن **مش رخصة واحدة**. الجدول الكامل (ملف · مؤلف · رخصة معلنة ·
مصدر تاني مذكور) في [`docs/gl-transitions-headers.md`](gl-transitions-headers.md)، متولّد من الملفات
نفسها بـ`python3 tools/gl_headers.py --write`:

- 187 ملف رأسه بيقول `License: MIT`.
- `InvertedPageCurl.glsl` — `License: BSD 3 Clause`، وفيه نص حقوق Hewlett-Packard (2010) كامل.
- `StereoViewer.glsl` — `License: BSD 2 Clause`، وفيه نص حقوق Theodore K Schundler (2016) كامل.
- ملفات تانية رخصتها المعلنة MIT لكن بتذكر مصدر تاني جواها (Shadertoy، gist، مكتبة noise، سطر
  حقوق للمؤلف) — متعلّمة في الجدول تحت "Files that need a look".

الجدول **نقل للي الملفات بتقوله، مش قرار قانوني**. اللي لسه **غير محسوم** ومحتاج قرار من صاحب المشروع:

1. المستودع الأصلي مابيعلنش رخصة SPDX واحدة (GitHub: `NOASSERTION`) — هل الرؤوس كافية؟
2. ملفات BSD بتشترط بقاء نص الحقوق عند إعادة التوزيع — النص موجود جوه الملفين؛ هل مطلوب حاجة زيادة؟
3. الملفات اللي بتذكر مصدر تاني: هل رخصة المصدر ده متوافقة مع اللي الملف معلنه؟
4. مفيش ملف `LICENSE` ولا رقم commit للمصدر جوه `assets/gl-transitions/`.

لحد ما ده يتحسم: ماتعيدش توزيع المخزن بره المشروع على إنه MIT.
