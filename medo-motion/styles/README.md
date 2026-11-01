# الستايلات — ستايلك أنت أولاً

**المهارة ما تحبسك في ستايلات معيّنة.** ستايلك الخاص هو الأساس: مراجعك والإحساس اللي تبيه، مع ألوان وخطوط هوية ميدو المقفولة. أي وكيل داخل الريبو يقدر يبني وصفة ستايل للمشروع ويحفظها في `STYLE.md`.

الملفات هنا **أمثلة للإلهام**. تقدر تبدأ من واحد، أو تخلط بين اثنين، أو تتجاهلها كلها. `STYLE.md` في جذر المشروع يوثّق وصفة الفيديو الحالي؛ أما `styles/` فيحفظ الستايلات القابلة لإعادة الاستخدام.

## كيف تبني ستايلك
- **عندك مرجع فيديو؟** ضعه في `projects/<slug>/assets/refs/`، حلّله بالأمر الموضّح في `docs/reference-workflow.md`، ثم لخّص التكوين والحركة والإيقاع في `STYLE.md`. التحليل يصف المرجع؛ ألوانه لا تستبدل بالِت ميدو، ومحتواه/شعاره/أصوله لا تُنسخ.
- **عندك هوية؟** أعطه شعارك، وألوانك، وخطك: «هذي هويتي، سوّ ستايل عليها».
- **ما عندك شي؟** قل: «اقترح لي ٣ اتجاهات تناسب فكرتي». Claude يصمم لك اقتراحات جديدة. الأمثلة تحت مجرد نقطة بداية.
- **احفظ اتجاهًا متكررًا:** «احفظ هذا الستايل باسم [الاسم]». خزّنه في `styles/` داخل **مشروعك** من القالب `_template.md` لاستخدامه لاحقًا. وصفة كل فيديو تظل في `STYLE.md`.

## أمثلة للإلهام
| المثال | الإحساس | الملف |
|---|---|---|
| **الشرح التحريري** (Editorial Explainer) | ورق، وواجهات، ونقاط طباعة، وإيقاع سريع. للشروحات والأدوات | `editorial-explainer.md` |
| **العرض** (Showreel) | قوي، سريع، واثق | `showreel.md` |
| **الطرفية** (ASCII Terminal) | تقني، غامض | `ascii-terminal.md` |
| **بكسل** (Pixel Art) | ألعاب، حنين | `pixel-art.md` |
| **الخط الواحد** (One-line Art) | هادي، بسيط | `one-line.md` |
| **قصاصات الريزو** (Risograph) | يدوي، دافئ | `risograph.md` |
| **دفتر الجزري** (Inventor's Notebook) | تراث، اختراع | `jazari-notebook.md` |
| **الحبر في الماء** (Ink in Water) | ناعم، فخم | `ink-in-water.md` |

**طريقة الإخراج غير الستايل:** ريلز الشرح والأدوات والقوائم لها نظام إخراج كامل في `reference/explainer-reel-system.md`، ويشتغل مع **أي** ستايل، سواء ستايلك أو مثال من هنا.

## قواعد لكل الوكلاء | For every agent
- **Default to the user's own style.** Ask for their references, brand colours, fonts or mood first. Build a custom style from them (analyse references with `reference/reference-and-delivery.md`) and save it in the project's `styles/` from `_template.md`.
- Offer these examples only when the user has no direction, asks for options, or names one. Present them as starting points, never as the only choices; when proposing directions, design new ones fitted to the brief as well.
- When an example is used, record the project-specific adaptation in `STYLE.md` and `TASTE.md`; keep the preview/design file in sync if the project uses one. The end word «حركة» in each prompt is a placeholder.
- Every look with Arabic text obeys `reference/arabic-typography.md`. Download fonts with `scripts/get_fonts.py`; find sounds with `scripts/openverse_sfx.py`.
