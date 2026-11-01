# Changelog — Medo Motion (private fork)

## 1.6 — 2026-11-01 — transitions + a procedural sound kit
- **Transition catalogue** (`motion/transitions.json`, 14 entries): wipe, wipeUp, diagonal, iris,
  irisClose, slide, cover, blinds, checker, bands, dissolve, zoom, glitch, flash. Every entry declares
  its `kind`, easing and the sound it pairs with. Names/kinds are inspired by the MIT gl-transitions
  collection; the maths is vector/CPU so nothing depends on a GPU or on real time.
- **One geometry, two engines**: `templates/render/lib/transition.js` (`transitionLayer`,
  `makeLayer`, `compositeTransition`) and `templates/procedural-reels/transition.py` (`layer`,
  `composite`). Masks are normalised, so the same numbers paint the same picture;
  `tests/test_transitions.py` compares JS↔Python sample by sample and checks endpoint/invert behaviour.
- **Sound kit** (`templates/procedural-reels/sfx.py`): 15 synthesised, deterministic sounds with a
  `CATALOG` (family + base gain), a cue-sheet `bus()`, `duck()` for voice-over, `cues_for_transitions()`
  (cuts → hits via the transition catalogue) and `render_bank()` for editor imports.
- **Tools**: `tools/sfx_kit.py` (`--list`, `--bank`, `--demo`, `--cues … --vo … --out …`) and
  `tools/transitions_sheet.py` (contact sheet + preview clip with the matched sounds). `make sfx`,
  `make sfx-bank`, `make transitions`.
- **Equation easings**: `motion/easings.json` gained the Penner `formulas` family (elastic, bounce,
  quad/cubic/quart/quint, sine, expo, smoothstep) — names that don't collide with the bezier
  vocabulary, identical in both engines.
- **Engine K demo**: `scenes/transition-example.js` (25–28.2 s) cuts between two scenes through the
  catalogue; the reel template's duration is now 28.2 s.
- Docs: `docs/transitions.md`, `docs/audio.md`, motion doc updated; README/AGENTS/docs index/tools
  README/Makefile wired.
- Verified: `ruff` clean · `pytest` 113 passed · `make ci` OK · `selftest` PASS · sheet + clip inspected.

## 1.5 — 2026-11-01 — motion grammar (motion.dev + Theatre.js, without their runtimes)
- **`medo-motion/motion/easings.json`**: 12 named cubic-beziers with motion.dev's control points
  (easeIn/Out/InOut, circ…, back…, anticipate) + 5 spring presets + the brand's locked timings.
- **Deterministic motion module in both engines**: `templates/render/lib/motion.js` and
  `templates/procedural-reels/motion.py` — `ease`, closed-form `spring` (stiffness/damping/mass,
  overshoot included), `springDuration`, `keyframes`, `timeline().at(t)`, `stagger`, `reveal`.
  Same numbers in JS and Python (asserted numerically by the tests).
- **Timeline JSON format** (+ `motion/examples/card-entrance.json`): keyframe tracks with per-segment
  easing, colour interpolation, clamping outside the range.
- **Theatre.js bridge**: `tools/theatre_import.py` converts a Studio state export into our timeline
  (bezier handles → cubic-bezier, `--offset`, `--sheet`, `--list`).
- **Offline motion studio**: `tools/motion_studio.html` (JSON editor, scrub, play, live values,
  download) — imports the engine's module, so what you preview is exactly what renders. `make studio`.
- **Engine K demo**: `scenes/motion-example.js` (22–25 s) driven entirely by a timeline; visible in
  `make selftest` renders and the palette audit stays clean.
- Docs: `docs/motion.md` (what we took, what we deliberately skipped, recipes, limits),
  `motion/README.md`, README/AGENTS/docs index/tools README updated.
- Verified: `ruff check .` clean · `pytest` 87 passed · `make ci` OK · `selftest` all PASS.

## 1.4 — 2026-11-01 — the whole itshover library, inside both engines
- **Vendored itshover** (Apache-2.0, `itshover/itshover` on GitHub) into `icons/itshover/tsx/`
  with its LICENSE and upstream registry — 263 components, the complete set behind
  https://itshover.com/icons. The site itself is blocked from the sandbox, GitHub is not.
- **Importer** `tools/itshover_import.py`: reads each component's `<svg>` (path / rect / circle /
  ellipse / line / polyline / polygon, `fill`, `transform`, plus the JSX-array cases) and emits
  `icons/itshover/registry.json`. `--list` searches it, `--promote <id>` moves one icon into the
  house registry for Arabic labelling and hand edits.
- **Full SVG path support in the builder**: an SVG path parser/flattener (M L H V C S Q T A Z, arcs
  via endpoint→centre, packed arc flags) so curves, rounded rects and ellipses look identical in
  SVG, Canvas (native `Path2D`) and Pillow (flattened polylines). Filled shapes supported.
- **275 icons total** (12 house + 263 itshover, 41 of them third-party brand marks flagged
  `group: "brand"`), all palette-locked at draw time, all in `lib/icons.js`, `icons.py` and `svg/`.
- Fixed the engine-K painter origin (icons were drawn from the centre instead of centred) and
  scoped per-part transforms with save/restore.
- Docs: `docs/icons.md` rewritten (what is identical, what is intentionally different, commands),
  `assets/CREDITS.md` created with the Apache-2.0 attribution, README/AGENTS/CHANGELOG updated.
- Verified: `ruff check .` clean · `pytest` 76 passed · `icons --check` in sync.

## 1.3 — 2026-11-01 — palette v2 + animated icon layer
- **Palette v2 (from Medo):** the 12 supplied colours replace the old red/black/yellow/teal set;
  one derived shade `ink_shadow #2E2423` (ink −35%). `brand/brand.json`, `brand/BRAND.md`,
  `templates/TASTE.md`, `styles/medo-red-circle.md` rewritten; ~150 colour literals remapped in
  engine P (`lib.py`, `art.py`, `scenes.py`) and engine K (`lib/brand.js`, `lib/kit.js`, scenes).
  No yellow/green/blue left: positive emphasis is paper white + ✓.
- **Brand guard rewritten:** contrast pairs now measured on the real surfaces (paper-on-ink 9.83,
  red-on-paper 4.88, blush-on-ink 5.46) and forbidden pairs asserted low (red-on-ink 2.01).
  `brand_check.py --project medo-motion/templates` also fails on any off-palette literal in either
  engine — the check runs in `make ci` and in the tests.
- **Animated icon layer (`medo-motion/icons/`):** one `registry.json` (12 icons, Arabic labels,
  primitives on a 24×24 grid) generates animated SVGs, `templates/render/lib/icons.js` (canvas
  `drawIcon`) and `templates/procedural-reels/icons.py` (Pillow `draw_icon`). Colours are passed at
  draw time, so icons cannot leave the palette. `examples/PlugConnectedIcon.jsx` + `components.json`
  document the itshover/`shadcn add` path (itshover.com is unreachable from the sandbox).
- **QA tooling:** `tools/icons_sheet.py` (engine P sheet), `tools/icons_preview.mjs` (engine K sheet
  via Chromium), `make icons`, `icons --check` in CI, `tests/test_icons.py`.
- **Engine K demo:** `scenes/icons-example.js` (18.5–22 s) shows the six laptop-part icons animating.
- Verified: `ruff check .` clean · `pytest` 60 passed · `tools/selftest.py` all PASS · `make ci` OK.

## 1.2 — 2026-11-01 — clean-code pass
- **Tests:** `tests/` with 26 pytest cases — Arabic shaping invariants (joined forms,
  visual run order, number separators, ink-tight sprites, strokes keeping counters,
  determinism, anchor centring), the brand lock (tokens, no-logo rule, JS↔JSON sync,
  contrast), the scaffold, and one real 1080×1920 engine-P frame.
- **Self test:** `tools/selftest.py` (doctor → tests → engine P render → engine K render)
  and a `Makefile` (`make setup|doctor|test|selftest|new|brand|clean`).
- **Lint:** `pyproject.toml` with ruff (E4/E9/F/I/UP/B), documented per-file ignores for
  the vendored engines' compact style. `ruff check .` is clean.
- **Code cleanups:** removed dead imports/locals in `art.py`, `scenes.py`, `mix.py`,
  `brand_check.py`; `lib.py` gained `_shaper()` instead of duplicated backend guards;
  `arabic_shape.py` got named constants (`BIDI_MARKS`, `NUMBER_SEPARATORS`), typed run
  splitting, `__all__` and a context-managed font read; `doctor.py` de-duplicated.
- **Repo hygiene:** `docs/` (analysis + conventions), `tools/README.md`,
  `tools/requirements.txt`, `.editorconfig`, `.github/workflows/ci.yml`, and a
  `.gitignore` that covers render output, caches and secrets.
- Verified: `ruff check .` clean · `pytest` 26 passed · `tools/selftest.py` all PASS.

## 1.1 — 2026-11-01 — agent-agnostic studio + new contract
- **Works with any coding agent.** The operating contract moved to `AGENTS.md` at the
  repo root; `SKILL.md` now defers to it and no longer assumes Claude Code.
  Added `tools/setup.sh`, `tools/doctor.py`, `tools/new_project.py`.
- **Contract changed to four inputs:** script · scene direction · Medo's VO · Medo poses.
  Everything else (visuals, SFX, music, timing, assets) is produced by the agent.
- **Removed the logo and the series name everywhere.** No chip, no episode number, no
  reserved logo circle in `scenes.py`; `brand.json` (`logo: null`, `logo_rule`),
  `BRAND.md` §1/§6/§10, `TASTE.md`, `medo-playbook.md` §1/§7 updated. End cards are
  typographic only. The ElevenLabs onboarding flow was dropped: VO comes from Medo,
  TTS is opt-in only.
- **New Arabic shaping fallback** `templates/procedural-reels/arabic_shape.py`
  (HarfBuzz shaping + FreeType rasterising) for Pillow builds without libraqm.
  Verified: joins, RTL run ordering, mixed Latin/digits, 25,000 / 12:30, strokes
  composited behind the glyphs, ink-tight sprites so caption layout is unchanged.
- **Engine K rebranded:** `data.js` loads Cairo, `lib/kit.js` FONTS default to Cairo,
  `explainer-example.js` loads Cairo only; `#E8322B` → brand `#E5262B`.
- `lib/brand.js`: background gradients (`bgDarkTop/Bottom`, `bgLightTop/Bottom`),
  `chipY` removed. `brand_check.py --project` now also audits `lib/brand.js`
  (colours, gradients, font, safe zones) and finds `src/lib` copies.
- `preflight.py`: the `medo` block no longer collapses to an error when Pillow is
  missing; it reports `arabic_shaping: raqm | harfbuzz-fallback | NONE`.
- `render.js`: accepts `playwright-core` (works with the bundled Chromium).
- **Loudness hardened** (`mix.py`): loudnorm aims at TP −2.0 (it overshoots its own
  target by ~0.2–0.4 dB), a limiter acts as the hard ceiling, and a final deterministic
  trim lands inside −14.5 ±0.3 LUFS while never exceeding −1.5 dBTP. Measured on a test
  mix: was −1.3 dBTP → now −14.7 LUFS / −1.5 dBTP.
- Engines honour `FFMPEG_BIN` when ffmpeg is not on PATH.
- Verified here: engine P 8-frame chunk + contact sheet with correct Arabic captions and
  a 90-frame master (1080×1920, H.264+AAC, 4.5 Mbps, faststart); engine K 12 frames
  through Chromium 153; mix + two-pass loudnorm; `brand_check` PASS; `doctor.py` READY
  except the optional drawtext filter.

## 1.0 — 2026-11-01 — fork of Khaam Motion 1.4.1
- Added `brand/` (BRAND.md + brand.json), `styles/medo-red-circle.md`, `reference/medo-playbook.md`, `scripts/brand_check.py`, `templates/render/lib/brand.js`; `templates/TASTE.md` pre-filled with locked brand values.
- Added `templates/procedural-reels/` extracted from AGENT_MASTER_BRIEF_v4 and made portable: relative paths, Cairo-first font resolver (variable-font bold), brand-silhouette PLACEHOLDER when Medo poses are missing, `cutout.py` CLI, cross-platform `run_all.py`.
- Encode changed to the brief's MASTER spec (CRF 13, tune animation) — the brief's appendix code still used CRF 17/fast.
- Fixed: chunk files now carry start+end in the name and `run_all.py` deletes stale chunks when code/assets/timings change (the original silently reused them).
- Dialect switched from Gulf to Egyptian. Normalised line endings to LF.
- Tested here (Linux sandbox): 8-frame contact sheet, 45-frame chunk encode (4.9 Mbps), chunk resume + stale invalidation, two-pass loudnorm (−14.5 LUFS, TP −5.1). NOT tested: Windows, real Cairo font, real Medo poses, full 55 s render.

# سجل الإصدارات — «موشن خام»

## 1.4.1 — 2026-10-26 — راشد الحازمي (خام)
- **نطق الاختصارات في الصوت المعلّق** (`reference/voiceover.md`): الاختصارات اللي تنقرى حرف حرف (SEO، GPT) تنكتب بالإنجليزي وبحروف كبيرة في النص اللي يروح لـ ElevenLabs، مثل `Chat GPT`. والكلمات والأسماء الإنجليزية اللي تنقرى ككلمة تنكتب بالعربي مثل ما تنطق (قوقل، كلود كود)، وAI يمشي الاثنين. السبب: «سيو» بالحروف العربية انقرت "Co" بدل SEO. الكابشن على الشاشة ما تغيّر.

## 1.4.0 — 2026-10-26 — راشد الحازمي (خام)
- **المسار السريع: ٣ محطات بس.** (أ) رسالة خطة وحدة: ٣ هوكات، والسكربت، والستايل، وهل فيه صوت معلّق وتكلفته. (ب) لوحة storyboard وحدة. (ج) **أول معاينة توصلك كاملة**: حركة ومؤثرات وصوت معلّق مع بعض. بعدها النسخة النهائية بدقة كاملة.
- **ما فيه جولات زيادة:** لا معاينة صامتة، ولا جولة للصوت لحاله، ولا معاينة منفصلة لأول ٣ ثواني. الصوت يتولّد ويتركّب مع الحركة في نفس المرة، والفحوصات الداخلية (القياس والتزامن والعلو) يسويها Claude بنفسه بدون ما يعرضها عليك.
- **يتعلم ويتذكر:** الفيديو الجديد في نفس المجلد ياخذ ستايل آخر مشروع ويسأل سطر واحد: «نفس الستايل؟». وأي تفضيل عام تقوله ينحفظ في `~/.cache/khaam-motion/user-taste.md`، ويطبقه في كل المشاريع بعدها. والمستخدم الراجع ما يمر بالتعريف من جديد.
- `preflight.py` يقول هل ملف التفضيلات موجود.

## 1.3.0 — 2026-10-26 — راشد الحازمي (خام)
- **الهوك أولاً** (`reference/hooks.md`): قبل أي حركة، Claude يبحث عن هوكات مجالك (إذا عنده بحث في الإنترنت)، ويكتب ٣ خيارات (الجملة المنطوقة، والنص على الشاشة، وحركة أول ٣ ثواني)، وتختار واحد، ويبني أول ٣ ثواني ويعرضها عليك قبل الباقي. فيه ١٢ عائلة هوكات بقوالب عربية، وقواعد حركة أول ٣ ثواني.
- **إصلاح:** أداة الرندر والمعاينة صارت تفهم `~` و`%USERPROFILE%` و`$HOME` في ملف الإعدادات، مثل سكربتات Python. (اكتشفه Claude أثناء تجربة المهارة على مشروع حقيقي.) واسم `ffmpeg` بدون مسار صار يشتغل بعد.
- **اللغة:** نصائح نهاية التعريف الأول تطلع بلغة المستخدم بس (بدون عناوين إنجليزية).

## 1.2.0 — 2026-10-26 — راشد الحازمي (خام)
- **عرض الصوت المعلّق:** وقت التثبيت وأول مشروع، Claude يشرح الصوت بالذكاء الاصطناعي (ElevenLabs، نموذج Eleven v4): وش يضيف، وكيف تسوي مفتاح API وتربطه بأمان، والفرق بين الخطة المجانية والتجارية، وإنه يستأذن قبل كل طلب مدفوع. وإذا ما تبيه، يكمل موشن مع مؤثرات مجانية.
- **ما يتكرر:** الاختيار ينحفظ في `~/.cache/khaam-motion/onboarding.json`. المشاريع اللي بعدها تسأل سطر واحد بس في البداية: «تبي صوت معلّق ولا موشن بس؟».
- `preflight.py` صار يقول هل مفتاح ElevenLabs موجود (بدون ما يطبع قيمته)، وهل التعريف الأول انعمل.

## 1.1.0 — 2026-10-26 — راشد الحازمي (خام)
- **نظام ريلز الشرح** (`reference/explainer-reel-system.md`): طريقة إخراج كاملة لريلز الشرح والأدوات والقوائم، مستخلصة من تحليل ريلز ناجحة: هيكل السكربت (هوك برقم، ليش الحين، دليل، قائمة، «علّق الكلمة»)، والإطار الثابت (تسمية القسم، والتقدّم، والحساب)، ونظامين للكابشن (تحريري فوق، أو أزرار كيبورد تحت)، وقاعدة «لكل جملة صورة حرفية»، وانتقالات نقاط الطباعة أو العوالم اللونية، وخاتمة التعليق ثم الرسالة.
- **عُدّة العناصر** (`templates/render/lib/kit.js`): جوال، ونافذة برنامج وتيرمنال، وقائمة مهام، وبطاقة، ومجلد، وختم، وشارة، وعدّاد يدور، وشريط مقابس للتقدّم، ودائرة تحديد، وخطوط انفجار، ومسح بنقاط الطباعة، ونقاط طباعة للصور، وورق بحبيبات، ونهاية «علّق ← وصلتك الرسالة». كلها تحترم قواعد العربي.
- **مثال كامل بالعربي:** `templates/render/scenes/explainer-example.js` (11.5 ثانية).
- **الستايلات صارت أمثلة للإلهام:** ستايل المستخدم أولاً، وClaude يبنيه من مراجعه ويحفظه في مشروعه. شلنا 3 ستايلات خاصة بعلامتنا، وأضفنا مثال «الشرح التحريري».
- الفحص: معاينة contact sheet، وصور ثابتة، وMP4 كامل 1080×1920 مع مؤثرات CC0 من Openverse. انصلحت ملاحظتين: الصفر الهندي «٠» يشبه النقطة في التسميات (صارت 01)، ومسافة تعليق الخاتمة.

## 1.0.0 — 2026-10-26 — راشد الحازمي (خام)
أول إصدار عام.

- **ابدأ هنا:** تشغيل أول بالعربي. Claude يعرف هل أنت في تطبيق Claude أو Claude Code، ويوجهك للتثبيت والرفع (Customize ← Skills)، ويوصيك بـ Opus 5.5 مع effort ‏max، ويشرح كيف تضيف أشياءك بأمان.
- **طبقة العربي:** قواعد الكتابة العربية في الموشن (ما نكسّر الحروف، اتجاه RTL، الحركة بالكلمة أو بالقناع، الأرقام، والنصوص المختلطة) + مساعد `templates/render/lib/arabic.js` + مشهد عربي تجريبي.
- **فهرس الخطوط العربية:** خطوط مجانية (OFL) مع وصفها واستعمالها، وخطوط تجارية مع مصدرها. سكربت `scripts/get_fonts.py` ينزّل المجانية مع رخصتها.
- **مكتبة الستايلات:** 10 ستايلات جاهزة بالألوان والخطوط والحركة والصوت.
- **صوت مجاني:** `scripts/openverse_sfx.py` يبحث وينزّل مؤثرات من Openverse بفلتر الاستخدام التجاري، ويكتب ملف النسب تلقائياً.
- **الصوت المعلّق:** دليل Eleven v4 كامل، وسكربت `scripts/gen_tts_elevenlabs.py` (توليد، واستنساخ صوت بموافقة، وحوار).
- **storyboard قبل الرندر:** إطارات ثابتة للموافقة قبل الفيديو الكامل.
- الاسم «موشن خام»، ورخصة «خام»، ومتغيرات البيئة `KHAAM_*`، وإعداد المشروع في `.khaam/config.json`.

### الفحوصات اللي انعملت لهذا الإصدار (2026-10-26، Windows 11، Python 3.11، Node + Playwright Chromium)
- كل سكربتات Python تترجم (`py_compile`)، و`preflight.py` يشتغل ويقرأ إعداد `.khaam/config.json`.
- السكربتات الموجودة تشتغل بعد تغيير الأسماء: خطة الصوت المعلّق، وخطة المؤثرات، وفحص المكتبة، وخطة نماذج الصوت، وجرد الصوت.
- `get_fonts.py --check`: الـ 41 خط كلها موجودة في مستودع Google Fonts الرسمي برخصة OFL. تنزيل 3 خطوط مع الرخصة وملف المصدر وتسجيلها في `manifest.json`.
- عيّنة الخطوط: الـ 33 خط عربي رُندرت في Chromium وكلها أظهرت العربي صحيح (`reference/arabic-fonts-specimen.jpg`).
- `openverse_sfx.py`: بحث ببدون مفتاح، وتنزيل صوت CC0 وصوت CC BY. سطر النسب انكتب للـ CC BY بس، والسكربت رفض الكتابة فوق ملف موجود.
- الرندر: المشهد العربي (كلمات كاملة، كشف من اليمين لليسار، شريط يمشي من اليمين) بخط Kufam، معاينة contact sheet، وMP4 كامل 1080×1920 مع صوت. الحروف متصلة، والشدة والنقاط سليمة.
- ما انجرّب: رفع المهارة في تطبيق Claude (Customize ← Skills)، وmacOS وLinux، وطلبات ElevenLabs المدفوعة، وجلسة مبتدئ كاملة من الصفر.
