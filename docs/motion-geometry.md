# المرحلة الثالثة: تخطيط وعناصر حتمية للرندر

أدوات أصلية تعمل على بيانات مؤلَّفة وزمن محلي للمشهد، بلا Motion runtime أو قياس حيّ أثناء أخذ الإطارات. المصدر: `lib/motion-geometry.js` في K وR (نسختان متطابقتان) و`motion_geometry.py` في P. ليست هذه واجهة تأليف أو تحريكًا من مدخلات المستخدم؛ نفس الخطة والزمن ينتجان العينة نفسها حتى مع seek عكسي.

## تخطيط المجموعة وإعادة الترتيب

```js
import {stackLayout, reorderLayout, compileLayout, layoutBindings} from '../lib/motion-geometry.js';
import {drawGeometry} from '../lib/geometry-canvas.js';
const cards = [{id:'a',w:220,h:120,r:18},{id:'b',w:220,h:120,r:18}];
const options = {x:140,y:400,gap:24,axis:'y'};
const group = compileLayout({version:1, initial:stackLayout(cards,options), events:[
  {at:0.4,duration:0.5,mode:'sync',items:reorderLayout(cards,['b','a'],options)}
]});
// داخل draw(ctx,t): t بالثواني المحلية، وليس wall clock.
drawGeometry(ctx, layoutBindings(group.at(t), {colors:{a:'gray1',b:'gray2'}}));
```

الـIDs فريدة داخل المجموعة (حتى 256 عنصرًا) وتربط العنصر نفسه عبر snapshots؛ الأحداث لا تتداخل. `stackLayout` يدعم x/y/grid وRTL (x في RTL هو الحد الأيمن)، و`reorderLayout` يتطلب permutation كاملة. grid يستخدم عرض الخلية الأكبر في الصفوف. في Python الأسماء `stack_layout`, `reorder_layout`, `compile_layout`, `layout_bindings` والخيارات dict مماثلة. يمكن تغذية العينات مباشرة إلى `GeometryBindings` في R أو `draw_geometry` في P؛ الـadapter يرتب `overlay` بعد `flow`.

- `sync`: خروج ودخول وانتقال متزامن داخل مدة D. `popLayout`: الخروج على طبقة overlay، وبقية العناصر تنتقل داخل D. `wait`: خروج D، ثم انتقال D، ثم دخول D؛ نافذته **3D** حتى لو لا يوجد داخل أو خارج. توجد `duration` محسوبة على الخطة؛ يجب أن تتسع داخل توقيت الـVO الحقيقي، ولا تمدد مدة الفيلم تلقائيًا.
- `at(t)` يرجع id وbox وopacity وphase وlayer. تتغير الأحجام الرقمية مباشرة؛ النص يُرسم منفصلًا بالحجم الحقيقي، ولا يُكبَّر معه تلقائيًا. لا يوجد ربط تلقائي بين مجموعات مستقلة أو DOM snapshots عامة.
- `correctScale({scaleX,scaleY,radius,strokeWidth})` / `correct_scale` يعطي `radiusX/Y` و`strokeX/Y` عكس المقياس الموجب لكل محور. هذا حساب للمحاور فقط، ولا يصلح CSS transforms اعتباطية أو shadows أو stroke scalar تحت مقياسين مختلفين. الأفضل رسم الهندسة بالحجم النهائي.

## قياس النص العربي

حمّل خطًا معروفًا قبل القياس، ولا تفصل حروف العربي. في K/R `measureTextFit(ctx,text,options)` من `text-measure.js`: يتحقق من وجود FontFace محمّل بالاسم والوزن المطلوبين؛ ثم يقيس كلمات كاملة باستخدام Canvas ويختار أكبر حجم من `maxSize` نزولًا بخطوة `step` داخل `maxWidth` و`maxHeight`. احفظ النتيجة قبل الرندر، وارسم أسطرها بوسائل directed text. `padding` و`lineHeight` بالوحدات الرقمية؛ `fits:false` يعني عدم الرندر التلقائي أو القص الصامت.

في P استخدم `measure_text_fit(font_path,text,options)` من `text_measure.py` الذي يستخدم HarfBuzz/FreeType الحقيقي ويقيس الكلمات الكاملة. على المؤلف التأكد أن مسار الخط يطابق family/weight المكتوبين؛ Python لا يستخرج هوية الوجه للتحقق. P يقيس صورًا بها padding داخلي، وCanvas يستخدم مقاييس المتصفح؛ النتائج ليست متطابقة pixel-by-pixel. `fitMeasuredText` / `fit_measured_text` يقبل مرشحين مقاسين مسبقًا، لكنه يثق بصحة المقاييس؛ لا تستخدم أرقامًا مخمنة على أنها قياسات حقيقية. تجنب خطًا غير محمّل أو fallback مختلفًا، وتحقق بصريًا من تشكيل النص وحدود الكادر.

## الرسم والمزج والربط

- `strokeSegments(points,{start,end,offset,closed})` / `stroke_segments`: أجزاء خط متعدد النقاط بحسب طول المسار، من 0 إلى 1، مع offset ملتف؛ لا يقرأ SVG path أو Bezier مباشرة؛ [compiler محدود لـSVG](motion-svg.md) يحوّلها أولًا إلى نقاط. دوال الرسم ترسم القطع باللون المعتمد؛ path المغلق يمكن تعبئته، وstroke يظل مستقلًا عن التعبئة.
- `compileMorph({from,to,count,closed,align})` / `compile_morph`: إعادة أخذ عينات متساوية الطول لـpolyline أو حلقة واحدة (حتى 256 عينة)، ثم مزج عند progress. المحاذاة اختيارية للحلقة وتضبط winding ونقطة البداية. هذه الدالة ليست parser لـSVG، ولا تدعم الثقوب أو عدة حلقات (يوجد [adapter محدود للحلقات المتوافقة](motion-nested-morph.md))، ولا يضمن عدم التقاطع الذاتي أو تطابق topology.
- `compileBindings({version:1,bindings:[...]})` / `compile_bindings`: يربط tracks بمفاتيح هندسية مسموحة فقط لـrect/circle/path؛ القيم من sampler مؤلَّف، والألوان palette tokens أو null. لا eval أو HTML أو CSS عامة، ويفشل عند خصائص غير مدعومة أو قيم غير صالحة. `boxStyle` / `box_style` يرجع CSS رقميًا منظّمًا لمستطيل، دون parsing لقيم CSS الاعتباطية. K `drawGeometry`، R `GeometryBindings`، P `draw_geometry` تستهلك مخرجات validated bindings. حواف P تُقرّب للبكسل؛ لا وعد بتطابق raster بين المحركات.

لا تتجاوز هذه الأدوات بوابات الحقائق أو العربية/الهوية أو مراجعة safe zones. استخدم أزمنة VO المقاسة ولا تجعل العينة تُظهر رقمًا أو نصًا قبل مرساته الصوتية؛ fixture هنا مثال اصطناعي، ليس فيلمًا معتمدًا.

## إعادة التحقق

```bash
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 -m pytest tests/test_motion_geometry.py -q
python3 tools/visual_verify.py --out cache/new-geometry-proof --geometry --replay --remotion
bash tools/ci.sh
python3 tools/selftest.py --remotion --hybrid
```

المخرجات الصناعية تشمل لقطات P/K/R، وK صامتًا بثلاث ثوانٍ، وفحص K للـlayout وseek عكسي عبر الإطارات. هذا ليس إثبات VO ولا تكافؤ بكسلات بين المحركات. يمكن تشغيل CI وselftest بالتتابع فقط لأنهما يستخدمان مسارات توليد مشتركة.
