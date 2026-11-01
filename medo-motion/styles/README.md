# الستايلات — ستايلك أنت أولاً

**المهارة ما تحبسك في ستايلات معيّنة.** ستايلك الخاص هو الأساس: ألوانك، وخطوطك، ومراجعك، والإحساس اللي تبيه. Claude يبني لك ستايل كامل منها ويحفظه في مشروعك.

الملفات هنا **أمثلة للإلهام**. تقدر تبدأ من واحد، أو تخلط بين اثنين، أو تتجاهلها كلها.

## كيف تبني ستايلك
- **عندك مراجع؟** أرسل فيديوهات أو صور أو حسابات تعجبك، وقل: «حلّل هذي وابنِ لي ستايل منها». Claude يطلع الألوان، والخطوط، وطريقة الحركة، والصوت، ويطبقها بطابعك.
- **عندك هوية؟** أعطه شعارك، وألوانك، وخطك: «هذي هويتي، سوّ ستايل عليها».
- **ما عندك شي؟** قل: «اقترح لي ٣ اتجاهات تناسب فكرتي». Claude يصمم لك اقتراحات جديدة. الأمثلة تحت مجرد نقطة بداية.
- **احفظه:** «احفظ هذا الستايل باسم [الاسم]». ينحفظ في `styles/` داخل **مشروعك** من القالب `_template.md`، وتقدر تستعمله في كل فيديو بعده.

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

## For Claude
- **Default to the user's own style.** Ask for their references, brand colours, fonts or mood first. Build a custom style from them (analyse references with `reference/reference-and-delivery.md`) and save it in the project's `styles/` from `_template.md`.
- Offer these examples only when the user has no direction, asks for options, or names one. Present them as starting points, never as the only choices; when proposing directions, design new ones fitted to the brief as well.
- When an example is used, copy its values into the project's `TASTE.md` §2–§5 and `plan/design.html`, then adapt them to the brief. The end word «حركة» in each prompt is a placeholder.
- Every look with Arabic text obeys `reference/arabic-typography.md`. Download fonts with `scripts/get_fonts.py`; find sounds with `scripts/openverse_sfx.py`.
