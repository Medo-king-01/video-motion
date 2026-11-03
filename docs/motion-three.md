# المرحلة الثامنة: طبقة Three اختيارية محدودة لـK

**حالة الميزة: جزئية وتجريبية.** `createThreeLayer` يرسم مشهد Three على WebGL2 canvas منفصل ويضع صورته في canvas المحرك K، عند زمن محلي صريح. لا يضيف Motion runtime أو `motion/three` أو واجهة تأليف، ولا يغيّر الرندر القائم إذا لم يستورده المشهد. لا يوجد adapter لـP أو R أو vgpu؛ يمكن استخدام K داخل Hybrid كمقطع متتابع، وليس كطبقة متزامنة مع محرك آخر.

## الاعتماد والترخيص

بعد [الدراسة والفحص](motion-gpu-feasibility.md)، ثبتنا **اختياريًا فقط** `three@0.187.0` (`REVISION` = `187`) في `tools/optional-three/package-lock.json` لاختبارات التكامل. رخصته MIT، copyright © 2010–2026 three.js authors؛ ترخيص الحزمة داخلها `LICENSE`. metadata لهذا الإصدار لا تسجل dependencies تشغيل عابرة. هذه مراجعة أولية وليست تدقيقًا أمنيًا؛ عند إعادة التوزيع احتفظ بإشعارات الرخص المطلوبة وراجع الإصدار واعتمادياته.

المحركات العادية و`tools/setup.sh` **لا تثبت** هذه الحزمة. لتنفيذ الاختبارات الاختيارية:

```bash
npm ci --prefix tools/optional-three --ignore-scripts --no-audit --no-fund
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 -m pytest tests/test_three_layer.py -q
```

اختبار المتصفح يتخطى إذا لم توجد الحزمة الاختيارية أو toolkit، فلا تخلط skip مع PASS. في مشروع K أو Hybrid محدد يرغب مؤلفه في هذا التكامل، ثبّت الإصدار نفسه في **جذر المشروع** قبل استخدام المشهد، مع حفظ lockfile الخاص به:

```bash
cd projects/my-reel
npm install --save-exact --ignore-scripts --no-audit --no-fund three@0.187.0
```

هذا أمر اختياري يغيّر package/lock للمشروع ويحتاج وصولًا إلى registry أثناء التثبيت؛ الرندر بعد التثبيت يستخدم الملفات المحلية. K يخدم `/node_modules/three/build/` من المشروع كما يخدم بقية الملفات المحلية. لا تستورد أمثلة أو أصولًا مدفوعة، ولا تُشغّل scripts من الحزمة. راجع `docs/motion-gpu-feasibility.md` لشروط Motion+ التي تبقى مستقلة ومعلّقة.

## عقد الاستخدام

```js
// في src/scenes/my-scene.js، بعد التثبيت المحلي أعلاه:
import * as THREE from '/node_modules/three/build/three.module.js';
import {createThreeLayer} from '../lib/three-layer.js';
let layer;
export function init({resources}) {
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-2, 2, 2, -2, 0.1, 20);
  camera.position.set(0, 0, 5); camera.lookAt(0, 0, 0); camera.updateProjectionMatrix();
  let mesh;
  // يُسجَّل renderer أولًا، فتنظف أصول المشهد المسجلة بعده قبله بترتيب LIFO.
  layer = createThreeLayer({THREE, width:512, height:512, scene, camera, resources,
    update(t) { mesh.rotation.set(0.25, 0.2 + t, 0); }});
  const geometry = new THREE.BoxGeometry(2, 2, 2);
  resources.defer(() => geometry.dispose());
  const material = new THREE.MeshBasicMaterial({color:'#D5AEA6'});
  resources.defer(() => material.dispose());
  mesh = new THREE.Mesh(geometry, material); scene.add(mesh);
}
export function draw(ctx, t) {
  layer.draw(ctx, t, {x:180, y:560, w:720, h:720});
}
```

- `width` و`height` أعداد صحيحة 2–4096، والمجموع حتى 4,194,304 بكسل؛ مستطيل الرسم finite وموجب. لا تفترض أن المستطيل داخل safe zones: راجعه.
- `update(t)` متزامن ويكتب **كل** القيم المتغيرة المطلوبة من الزمن المحلي كل مرة؛ يمكن أخذها من `compileSequence().at(t)`. زوايا Three بالراديان، ولا يوجد تحويل تلقائي إلى واجهة Motion بالدرجات. لا timers أو live inputs أو حالة تعتمد على الإطار السابق. المساعد لا يستطيع إثبات نقاء callback.
- الطبقة تملك **renderer فقط** وتسجيل إغلاقه في `resources`؛ المؤلف يملك الهندسة والمواد والخامات وكل مورد آخر، ويسجل disposers مباشرة بعد الإنشاء. لا traverse/cleanup تلقائيًا للموارد المشتركة. الإغلاق متكرر آمن؛ فشل سياق أو update أو تنظيف يفشل الرندر. لا ضمان عند kill/crash. إنشاء سياقات كثيرة قد يتجاوز حد المتصفح؛ لا يوجد مجدول أو إعادة استخدام تلقائي للسياقات.
- canvas شفاف (`alpha`, `preserveDrawingBuffer`) بلا antialias، pixel ratio = 1؛ `drawImage` يركّبه على الكانفس الحالي. `scene.background` أو المواد أو التحويلات قد تجعل المحتوى معتمًا أو تغير الألوان؛ اختبر الشفافية واللون والحواف على جهاز الرندر. لا تحميل أصول أو network يقوم به helper؛ المستخدم مسؤول عن أصوله، واستخدم ملفات محلية فقط.
- لا يوجد reduced motion تلقائي أو تصريح للإتاحة. إذا أردته، صمّم البديل الزخرفي للمشهد مع `supportsReducedMotion=true` و`motionMode` في `init`/`draw` كما في [عقد الرندر](motion-render.md). لا تغيّر توقيت ظهور حقيقة أو نص أو VO.
- يمكن رسم الـ3D فقط بعد توقيت/مرساة الحقيقة المقاسة، لكن helper نفسه لا يعرف الحقائق ولا يسجل bounds لـ3D في layout audit. احتفظ بالنص العربي بخط موجه وأدوات النص الأصلية؛ لا تستخدم texture نصية كبديل لفحص العربية.

## ما اختُبر وما لم يُختبر

المشهد الاصطناعي `tests/fixtures/visual/three-scene.js` يستخدم cube محليًا و`compileSequence` ويثبت وضع reduced صراحةً. على Chromium/SwiftShader في جلسة واحدة: طبقة شفافة، 30 إطارًا 1080×1920، و30/30 تطابق reverse-seek مع صفر مشاكل text layout مسجلة. رُندر K داخل Hybrid بمقاطع P/K/R في الوضعين (18 إطارًا/0.6 ثانية)، وصوت **صامت اختباري**. المقطع/الصور والتقارير في `cache/motion-phase8-proof/`، وليست تسليم إنتاج أو إثباتًا لمرساة VO حقيقية.

هذا اختبار WebGL2 برمجي في متصفح واحد، لا اختبار GPU عتادي أو ضمان تطابق البكسلات عبر الأجهزة أو السواقات أو إعادة فتح المتصفح. لم تُختبر المواد والشادرز/الإضاءة/الخامات عمومًا ولا P/R 3D. profile K يقيس capture/write وflush لكن لا يعزو وقتًا إلى GPU. اختبر المشهد الفعلي مع `tools/gpu_preflight.mjs`, `--audit --replay`، فحص بصري، VO وrender نهائي على بيئة التسليم. استخدم P/K/R التقليدية كبديل إذا فشل WebGL؛ لا fallback صامت.
