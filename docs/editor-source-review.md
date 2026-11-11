# مراجعة مصادر المنصة — قراءة ساكنة أولية

راجَعنا المستودعين عند الـcommits المحددة أدناه؛ هذه قراءة لبعض الملفات الفعلية، **ليست اختبارًا
تشغيليًا أو جردًا كاملًا أو مراجعة قانونية**. قبل هذه المراجعة اعتمدت الوثيقة على خريطة المستخدم
ومستودع Video Motion فقط. لم ننسخ كودًا أو أصولًا من المستودعين في هذه الدفعة.

## Hojas Studio — `e91244cb1286968b6a554e42a6f9f1d2f3fa86ac`

- [LICENSE](https://github.com/rakaga66/hojas-studio/blob/e91244cb1286968b6a554e42a6f9f1d2f3fa86ac/LICENSE):
  PolyForm Noncommercial 1.0.0؛ الاستخدام المسموح وشروطه في نص الترخيص. لا ننقل الكود/القوالب أو
  الأصول إلى المشروع على أساس إباحة تجارية مفترضة. أفكار عامة فقط، وتنفيذ أصلي بعد مراجعة ملائمة.
- [studio.md](https://github.com/rakaga66/hojas-studio/blob/e91244cb1286968b6a554e42a6f9f1d2f3fa86ac/engine/references/studio.md)،
  [studio.py](https://github.com/rakaga66/hojas-studio/blob/e91244cb1286968b6a554e42a6f9f1d2f3fa86ac/engine/studio/studio.py)،
  [واجهة الجوال](https://github.com/rakaga66/hojas-studio/blob/e91244cb1286968b6a554e42a6f9f1d2f3fa86ac/engine/studio/studio-mobile.html):
  توجد واجهة تحرير فعلية تكتب ملفات `studio.json` و`caps.json` وغيرها ويقرأها مسار الرسم؛ للواجهة
  تراجع snapshots وللقص undo منفصل. وجود timeline لا يثبت أنها محرر عام مكافئ للمواصفات التي نريدها؛
  لم نختبر كل عملياتها أو حفظها أو سلوكها عبر المنصات.
- [board.md](https://github.com/rakaga66/hojas-studio/blob/e91244cb1286968b6a554e42a6f9f1d2f3fa86ac/engine/references/board.md):
  الـBoard طبقة تصريحية تحتوي مشاهد وعناصر بتوقيت؛ المرجع يصف معاينة ورندر إطارًا بإطار. مناسب
  كفكرة لتمثيل قابل للتحرير لاحقًا، وليس تنفيذًا نقلناه أو اختبارًا لجودة الرندر.
- [clips.md](https://github.com/rakaga66/hojas-studio/blob/e91244cb1286968b6a554e42a6f9f1d2f3fa86ac/engine/references/clips.md)
  يصف تفريغًا وترشيحات ومراجعة اختيار الإنسان؛ مسار التفريغ مذكور باستخدام Whisper. لا يُنقل هذا
  الافتراض إلى نواة التحرير الحتمية بلا AI التي طلبها المستخدم.

## Video Ad Editor — `50f2cd4710608e7e656cae6d0b8ac465b45206f2`

- [LICENSE](https://github.com/majedphotos/video-ad-editor/blob/50f2cd4710608e7e656cae6d0b8ac465b45206f2/LICENSE)
  هو MIT، لكن [CREDITS للحركات](https://github.com/majedphotos/video-ad-editor/blob/50f2cd4710608e7e656cae6d0b8ac465b45206f2/video-ad-editor/motion/moves/CREDITS.md)
  يذكر مصادر وتراخيص مختلفة؛ افحص كل ملف وأصل ومصدر على حدة واحتفظ بإشعارات الترخيص المناسبة
  عند أي إعادة استخدام، ولا تعتبر الترخيص العام ترخيصًا تلقائيًا لكل أصل.
- [catalog.json](https://github.com/majedphotos/video-ad-editor/blob/50f2cd4710608e7e656cae6d0b8ac465b45206f2/video-ad-editor/motion/moves/catalog.json)
  يحتوي 102 مدخلًا، لكن **ليست كلها دوال رسم**: الكتالوج نفسه يميز قواعد توقيت، منها `jcut` و`matchCut`.
  [moves.js](https://github.com/majedphotos/video-ad-editor/blob/50f2cd4710608e7e656cae6d0b8ac465b45206f2/video-ad-editor/motion/moves.js)
  يحتوي فعلًا `pixelList` و`explode` و`riseUp` و`parallax`. `explode` المفحوص يرسم ألواحًا بإسقاط
  هندسي على Canvas؛ لا يثبت وجود نموذج 3D حقيقي للأجزاء أو تكامل جاهز مع Machine Kit عندنا.
  بعض الحركات تخزّن حساباتها في كائن الخيارات، فتحتاج مراجعة دورة الحياة والحتمية قبل أي تكييف.
- [podcast.md](https://github.com/majedphotos/video-ad-editor/blob/50f2cd4710608e7e656cae6d0b8ac465b45206f2/video-ad-editor/references/podcast.md)
  يصف المزامنة وخطة تبديل كاميرات، ويذكر اعتماد وضع الوجه والقص على Vision في Mac؛ لا نفترض دعم
  Windows أو دقة تتبع فعلية من الوثيقة. مسار الحلقة العريضة يذكر حدوده في التجربة الواقعية.
- [capcut.md](https://github.com/majedphotos/video-ad-editor/blob/50f2cd4710608e7e656cae6d0b8ac465b45206f2/video-ad-editor/references/capcut.md)
  يصف تصدير مسارات منفصلة وخطوات إغلاق CapCut وأخذ نسخة احتياطية؛ الموشن يوصف كـProRes شفاف،
  **مش بالضرورة عناصر موشن أصلية قابلة لتعديل كل خاصية**. لم نختبر التوافق مع إصدارات CapCut.

## أثر المراجعة على التنفيذ

نأخذ متطلبات عملية مثل خطط قابلة للمراجعة، تتبع المصدر عند القص، ورسائل رفض واضحة؛ لا نفترض
أن بنية أي مشروع أو اعتمادياته مناسبة مباشرة. الخطوة الحالية تنفيذ عمليات تحرير نقية على subset
الوسائط للمشروع الموحّد، وليس نقل واجهة أو محرك. الـBoard ومزامنة الكاميرات والتصدير للمحررات
تحتاج عقودًا واختبارات خاصة لاحقًا، مع مراعاة Windows والهوية والقواعد المعتمدة في هذا المشروع.
