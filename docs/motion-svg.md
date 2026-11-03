# SVG مستقر ضمن عقد محدود للرندر

هذا مسار **مستقر ومحدود** لملفات المسارات الثابتة، وليس رندرًا كاملًا لكل مواصفات SVG. لم نُدخل متصفحًا أو SVG runtime في P، ولا نحمّل ملفات خارجية وقت الرندر. يحوّل `tools/svg_compile.py` الملف محليًا إلى JSON هندسي موحد قبل رندر P/K/R. أي عنصر/خاصية غير مدعومة تُرفض بدل إهمالها بصمت. راجع الرخصة والمصدر قبل استخدام أي ملف.

## الاستخدام

```bash
export PATH="$PWD/.venv/bin:$PWD/tools/bin:$PATH"
python3 tools/svg_compile.py asset.svg plan/asset-svg.json --steps 32
```

يجب أن يكون ملف الخرج جديدًا. اقرأ JSON في مرحلة تهيئة المشهد، وليس داخل كل إطار. في K:

```js
import {drawSvgArt} from '../lib/svg-canvas.js';
// plan من ملف JSON المحلي الذي جرى تجميعه قبل الرندر
// progress اختياري، من 0 إلى 1؛ للتوقيت استخدم الزمن المحلي الصريح.
drawSvgArt(ctx, plan, {x:120,y:400,width:500,height:500,progress:0.7});
```

في R استخدم `<SvgArt plan={plan} x={120} y={400} width={500} height={500} progress={progress}/>` مع نوع `SvgPlan`. في P: `from svg_art import draw_svg_art` ثم `draw_svg_art(image, plan, {'x':120,'y':400,'width':500,'height':500,'progress':0.7})`. الأحجام الرقمية بالبكسل؛ يصغر/يكبر viewBox بنسبة موحدة مع توسيط، دون قص عند حد الصندوق. تأكد من الكادر وsafe zones بنفسك. `progress` يقتطع **كل contour مستقلًا** حسب طولها؛ التعبئة ثابتة ولا تُمسح مع stroke.

## المقبول والمرفوض

- `<svg viewBox="x y width height">` صريح، و`<g>` متداخلة، و`<path>` و`rect/circle/ellipse/line/polyline/polygon` الثابتة. مسارات M/L/H/V/C/S/Q/T/A/Z، صغيرة/كبيرة ومطلقة/نسبية وتكرار المعاملات، بما فيها arc flags المتجاورة، تتحول إلى polylines متعددة ومحدودة. تقريبات منحنيات ثابتة بـ4–64 خطوة لكل مقطع (`--steps`، الافتراضي 32)، **ليست حد خطأ هندسي مضمونًا**؛ راجع بصريًا وارفَع الخطوات عند الحاجة ضمن سقف النقاط.
- يجب التصريح بـ`fill` لكل path أو المجموعة الموروثة: `none` أو hex مطابق تمامًا لهوية ميدو، مثل `#CB271B`. لا تُقبل أسماء الألوان مثل `red` حتى لا يختلط أحمر SVG القياسي بلون الهوية المختلف. `stroke` كذلك و`stroke-width` رقم غير سالب. يجب تحديد `fill-rule="evenodd"` للتعبئة؛ عدة contours/ثقوب تعمل بـeven-odd. opacity للـpath تساوي 1 فقط. يُرسم stroke بنهايات وزوايا مستديرة؛ هذا أسلوب adapter واضح وليس الحفاظ على كل إعدادات stroke في المصدر.
- يدعم compiler تحويلات `matrix/translate/scale/rotate/skew` الثابتة (بما فيها المتداخلة)، ويطبقها على النقاط. عند وجود stroke مرئي يجب أن يكون التحويل المحصل مقياسًا موحدًا مع دوران/انعكاس، وإلا يُرفض بدل تشويه الخط. لا `style` أو CSS أو gradients أو filters أو masks أو clipPaths أو `<use>` أو text أو صور أو animations أو scripts أو شبكات أو DTD/entities. لا `nonzero` للتعبئة، ولا وحدات `px`/`%` للأبعاد؛ تُرفض هذه مدخلات صراحة. يُقبل XML declaration والتعليقات العادية، لكن DTD/entities وباقي processing instructions مرفوضة قبل التحليل. حوّل الأصول خارجيًا إلى مسارات ثابتة ومسطّحة ذات even-odd مع palette صريحة، ثم افحصها. لا تستخدم compiler كـsanitizer عام لتقديم ملفات XML خام للمتصفح.
- الوثيقة تقبل 256KB، 128 path، 64 contour لكل path، 1024 أمرًا لكل path، 4096 نقطة لكل contour و65536 نقطة إجمالية. إحداثيات وأبعاد ومدى المقياس مقيدة؛ المدخلات الخارجة تفشل. تحقق adapters أيضًا بنية JSON والـpalette قبل الرسم؛ لا يُنفذون markup.
- يوجد [morph محدود للحلقات المتعددة المتوافقة](motion-nested-morph.md) يطابق الترتيب المؤلَّف ويفحص الانتقال تحفظيًا؛ اختلاف topology أو المطابقة التلقائية أو morph SVG العام لا تزال غير منفَّذة. يمكن كذلك استخدام `compileMorph` على حلقة واحدة. لا مساواة pixel-perfect بين Pillow وCanvas وSVG DOM، خاصة الحواف والـstroke.

الاعتمادية التي تقوم بفك path هي `svgpathtools==1.7.2` (MIT) و`svgwrite==1.4.3` تبعية لها (MIT)، مقيدتان في `tools/constraints.txt` وتُثبتان مع `tools/setup.sh`. لا خدمات، ولا تحميل assets، ولا اعتماد GPU. الإشارات إلى SVG في مسارات أخرى من المستودع، ومنها registry الأيقونات، لا تتحول تلقائيًا إلى هذا العقد.
