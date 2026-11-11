# الصوت — مكتبة مؤثرات برمجية (Sound design kit)

## الفكرة | Why procedural
مكتبات المؤثرات المجانية كتير، بس كلها فيها نفس المشكلتين للريل بتاعنا:

1. **التزامن**: الهيت لازم يقع على فريم معيّن بالظبط. ملف جاهز محتاج قص وتدوير وتجربة، وممكن يبقى عنده
   transient غير حاد.
2. **الترخيص والـQA**: لازم تفتح الترخيص وتذكر المصدر، وتسمع كل ملف قبل ما تستخدمه.

عشان كده المكتبة هنا **متولّدة بالكود** (`templates/procedural-reels/sfx.py`): مجانية ١٠٠٪، أوفلاين،
و**حتمية** — نفس الـseed يطلّع نفس العيّنات بالظبط، فأي ميكس يتعمل تاني بنفس النتيجة على أي جهاز.

## الكتالوج | The kit (20 sounds)
| الصوت | عيلة | الاستخدام |
|---|---|---|
| `pop` | ui | لصقة/ماركر/رقم بيظهر |
| `blip` | ui | تأكيد صغير (٤٠ms) |
| `click` | ui | toggle |
| `tick` | ui | عدّاد، شرائط، تشيك ليست |
| `zip` | ui | خط بيتسحب، underline |
| `chime` | tonal | كشف/خبر حلو (FM bell) |
| `sparkle` | tonal | تفصيلة سحرية |
| `whoosh` | air | تغيير مشهد/wipe |
| `swipe` | air | slide/push/كروت بتتبدل |
| `noise` | air | dissolve / room tone |
| `riser` | build | تصعيد قبل impact |
| `impact` | impact | هبوط/جملة قوية |
| `stomp` | impact | جسم بيقع |
| `sub` | impact | وزن تحت قطع من غير ضربة |
| `glitch` | texture | glitch transition / لحظة خطأ |
| `snap` | ui | ضربة جافة (وش/wood block) للتركيز |
| `page` | ui | تقليب صفحة/مستند/تشيك ليست |
| `coin` | ui | سعر/مكسب/عدّاد (نغمتين معدنيين) |
| `heartbeat` | impact | توتر تحت كشف بطيء |
| `vinyl` | texture | كراكل/هيس — بيخلي البيت يبان مسجّل مش مولّد |

كل صوت عنده `family` و`gain` أساسي في `CATALOG` — الميكس بيبدأ من الـgain ده، فـ`gain: 1.0` في cue معناها
«بصوته الصح في الميكس»، مش «أعلى حاجة».

## الأوامر | CLI
```bash
python3 tools/sfx_kit.py --list                 # الكتالوج + المدد
python3 tools/sfx_kit.py --bank out/sfx         # WAV لكل صوت (للـeditor أو After Effects)
python3 tools/sfx_kit.py --demo cache/sfx.mp3   # معاينة مسموعة للكتالوج كله + كل الانتقالات
python3 tools/sfx_kit.py --cues cues.json --vo vo.wav --out mix.wav   # المدة = طول الـVO
python3 tools/sfx_kit.py --bank out/sfx48 --sr 48000                  # نفس الكيت بتردد 48k
python3 tools/sfx_kit.py --list --json                                # كتالوج للقراءة الآلية
```

> **الموسيقى والميكس الكامل** بقى ليهم أدوات مستقلة: `tools/music_kit.py` و`tools/audio_mix.py`.
> التفاصيل في **`docs/music.md`**. `--cues` هنا بيفضل شغّال زي ما هو (متوافق للخلف) لكنه بيعرف
> يعمل ducking بس للـSFX؛ الميكس الكامل (موسيقى + SFX + VO + loudnorm) بقى في `audio_mix.py`.
`make sfx` بيعمل المعاينة، و`make sfx-bank DIR=out/sfx` بيطلّع الملفات.

## شكل الـcue sheet
```json
[
  {"t": 1.20, "sfx": "whoosh", "gain": 0.9, "pan": [0.7, -0.7]},
  {"t": 2.05, "sfx": "chime"},
  {"t": 2.40, "sfx": "impact", "gain": 0.8, "seed": 4}
]
```
- `t` بالثواني من بداية الريل · `gain` و`pan` اختياريين · `pan` يقبل رقم أو (بداية، نهاية) للحركة.
- `sfx` لازم يكون من الكتالوج (غلط → خطأ واضح بالاسم).

بدل ما تكتبها بإيدك، اقدر تولّدها من **قطع المشاهد**: كل انتقال في `transitions.json` معلن الصوت بتاعه:

```json
{"cuts": [{"scene": 2, "t": 12.4, "name": "wipe"}, {"scene": 3, "t": 19.1, "name": "iris"}]}
```
```bash
# مفيش --length: طول الميكس = طول الـVO تلقائيًا (أو حدده صراحةً لو عندك سبب)
python3 tools/sfx_kit.py --cues cuts.json --vo vo.wav --out out/mix_raw.wav
```
كل cut بيتحوّل لصوته (`wipe` → `whoosh`، `iris` → `pop`، `glitch` → `glitch`…).

### على الشبكة | On the tempo grid
بدل ما تكتب وقت كل صوت بإيدك، اكتب **pattern** بحرف لكل ١/١٦ (bars = 4/4):

```bash
make grid PATTERN="k.h.|k.hh|k.h.|k..." BPM=120 BARS=2 OUT=cache/grid-cues.json
python3 tools/sfx_kit.py --cues cache/grid-cues.json --vo vo.wav --out out/mix_raw.wav
```
`k` impact · `s` click · `h` tick · `p` pop · `z` zip · `w` whoosh · `.` سكوت. النمط بيتكرر جوّه التاكت
عشان `bars` يفضل معناها بارات بالظبط، فالأصوات ما بتزيحش عن الضربة (`docs/rhythm.md`).

## الـanchors | Where the event sits
كل صوت بيعرف فين **الحدث** جوّه الموجة بتاعته: الـ`impact` في الأول، الـ`riser` في الآخر
(بيبان عشان يبقى ذروته عند اللحظة)، والـ`whoosh` في النص. الـ`bus()` افتراضيًا بيحط **بداية الملف**
عند الوقت (نفس السلوك القديم بالحرف)، ولو عايز الوقت يبقى هو لحظة الحدث:

```python
bus(6.0, [{"t": 3.0, "sfx": "riser"}], tail=True, anchored=True)   # الذروة عند 3.0 ث بالظبط
```

وده اللي بيخلي صوت الانتقال يقع على القطع نفسه مش قبله بنص ثانية.

## الحماية من الأخطاء الصامتة | No silent failures
- **القص مش مخفي**: `bus.last_truncated` بيقولك كام sample ما لقاش مكان. لو `> 0` يبقى في صوت اتقطع.
- **مفيش كتابة فوق ملف**: `render_bank(..., overwrite=True)` مطلوب لو الملف موجود.
- **معدل العيّنة بيتحترم**: كل المولّدات بتاخد `sr=` والفلاتر بتتبني من نفس المعدل (قبل كده كان
  `bp()` بيحسب على 44.1k حتى لو رندرت على 48k).
- **الـducking بمقياس مطلق**: الـenvelope بيتقاس على dBFS مطلق + lookahead، فالسطر الهادي بيتوتّى
  برضه (قبل كده كان بيتقسم على أعلى peak فالسطر الهادي ما كانش بيأثر).
- **طول الميكس محفوظ**: `duck()` بترجّع بطول الـbus مش بطول الـVO، فالـtimeline ما بتزحش.

## الميكس مع التعليق | Mixing
```python
from sfx import bus, duck, cues_for_transitions   # templates/procedural-reels/sfx.py
cues = cues_for_transitions(cuts, gain=0.9, pan=(0.6, -0.6))
vo_dur = len(vo_mono) / 44100            # طول الريل = طول التعليق، مش رقم ثابت
sfx_bus = bus(vo_dur, cues)
sfx_bus = duck(vo_mono, sfx_bus, depth=0.62)      # بيتوتّى تحت الكلام
```
والـmaster زي ما هو: `loudnorm` مرتين → limiter → **−14.5 ±0.3 LUFS، TP ≤ −1.5 dBTP**.
صوت أعلى من كده بيخسر على المنصات، وأوطى بيبان ضعيف.

لما تحتاج موسيقى + SFX + تعليق في **timeline واحد**، استخدم `tools/audio_mix.py` (شوف `docs/music.md`):

```bash
python3 tools/audio_mix.py --sheet cues.json --vo out/vo.wav --out out/final_audio.wav
```

`mix.py` القديم باقي زي ما هو لمشاريع engine P؛ الجديد بيغطي نفس الحاجة + الموسيقى + الـstems.

### المزيج القديم مابيتسلّمش في صمت (`pipeline.py`)

خطوة `mix` في `tools/pipeline.py` بتكتب `out/final_audio.mix.json` جنب الـWAV: hash لكل اللي المزيج
اتعمل منه — `out/vo24.wav`، قيم الـcue sheet (موسيقى، SFX، ducking، LUFS/true peak)، ملفات توليد
الموسيقى والـSFX والمزج نفسها (الموسيقى والـSFX متولّدين مش عيّنات)، وهل ffmpeg loudnorm متاح —
ومعاهم hash الـWAV الناتج. لو `final_audio.wav` موجود:

| الحالة | اللي بيحصل |
|---|---|
| السجل مطابق | بيتساب زي ما هو (إعادة تنسيق الـJSON أو `touch` مش تغيير) |
| أي مدخل اتغيّر، أو الـWAV نفسه اتبدّل، أو مفيش سجل (مشروع اتمزج قبل التحديث ده) | **`STALE` والخطوة بتفشل** برسالة فيها إيه اللي اتغيّر؛ مفيش ملف بيتلمس |
| `--remix` | بيعيد المزج فوق الـWAV ويكتب سجل جديد |
| `--keep-mix` | بيسيب الـWAV عمدًا ويسجّل إن الاقتران ده مقبول (أي تغيير بعده = `STALE` تاني) |
| مفيش cue sheet أصلًا | مزيج خارجي: بيتساب، والملاحظة بتقول إنه **مش متحقَّق منه** |

الاختيار: **رفض مش إعادة مزج تلقائي**. إعادة المزج بتكتب فوق ملف ممكن يكون اتعدّل بإيدك، والاحتفاظ
الصامت هو العطل الأصلي؛ الرفض مابيخسّرش حاجة ومابيسلّمش حاجة غلط. **الحد:** الفحص في خطوة `mix`
بس — تشغيل بـ`--from render` أو `--steps` من غير `mix` مابيفحصش.


## قواعد عملية | Rules that keep it sounding professional
- **hit واحد لكل معنى**: مش كل حاجة بتتحرك ليها صوت.
- **الانتقالات بس اللي بتاخد whoosh/swipe**، والتغيير الحقيقي (scene cut) ياخد `impact` أو `sub` تحته.
- **الـtick/pop** على الأرقام والعناصر، بحد أقصى ~٨ في الثانية، وبيخفّوا تدريجيًا.
- **التوتير**: خلي 0.6–1.2 ثانية بين أي صوتين في نفس العيلة.
- **التجربة على موبايل**: speakers صغيرة بتخفي `sub`؛ متعتمدش عليه لوحده.
- الأصوات كلها mono عدا الـpan؛ متحطّش reverb جاهز — `noise` يعمل air كفاية.

## إضافة صوت جديد | Adding one
```python
def tape_stop(seed=0, *, sr=SR):
    """..."""
    ...
BANK["tape_stop"] = tape_stop
CATALOG["tape_stop"] = dict(family="texture", gain=0.4, tags="pause, rewind")
ANCHORS["tape_stop"] = None        # None = احسبها من أعلى peak؛ أو 0.0 = ضربة، أو رقم ثواني
```
وبعدها `tests/test_sfx.py` بيتأكد من الحتمية والمدى والكتالوج، و`tests/test_sfx_engine.py` بيتأكد من
الـ48k والـanchor. ولو ربطته بانتقال: حط اسمه في `motion/transitions.json` → `sfx`.

> أي مولّد جديد **لازم** ياخد `*, sr=SR` ويستخدمه في كل فلتر — الـtests بتفشل لو معدل عيّنة اتغلب عليه.
