# أدوات هجرة مؤرشفة (one-off)

هذه السكربتات كانت تُشغَّل مرة واحدة أثناء بناء مكتبة الحركات من مصادرها الأصلية
(Alansari · Opus · gl-transitions · styles)، وهي **لا تعمل** على نسخة أخرى من المستودع:
كلها تحمل مسارات مطلقة (`/home/user/video-motion/...`) وأربعة منها تقرأ مدخلات من `/tmp/...`.
كذلك `generate_techniques_docs.py` يولّد أرقامًا قديمة (334) لم تعد صحيحة.

أُرشفت بدل حذفها لأنها توثّق كيف وُلّدت الأصول المضمّنة. نتيجتها محفوظة بالفعل ومغطاة باختبارات:

| السكربت | الناتج المحفوظ | الحرس الحالي |
|---|---|---|
| `add_variants.py` | متغيرات الحركات في `assets/techniques.json` | `tests/test_techniques.py` + `tools/sync_docs_numbers.py` |
| `merge_alansari.py` | 1,375 حركة Alansari | نفس الاختبارات |
| `merge_opus.py` | 616 حركة Opus | نفس الاختبارات |
| `merge_gl_transitions.py` | 189 انتقال GLSL | نفس الاختبارات |
| `extract_styles.py` | `assets/styles/styles.json` | `tests/test_styles.py` |
| `generate_techniques_docs.py` | `docs/techniques.md` (قديم) | `docs/techniques.md` الحالي + drift test |

**لا تستخدمها ولا تعوّل عليها.** لو احتجت إعادة نفس الهجرة مستقبلًا، اكتب أداة جديدة
تقرأ مساراتها من `tools/video_motion_paths.py` وتأخذ المدخلات من وسائط سطر الأوامر.
