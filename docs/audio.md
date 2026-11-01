# الصوت — مكتبة مؤثرات برمجية (Sound design kit)

## الفكرة | Why procedural
مكتبات المؤثرات المجانية كتير، بس كلها فيها نفس المشكلتين للريل بتاعنا:

1. **التزامن**: الهيت لازم يقع على فريم معيّن بالظبط. ملف جاهز محتاج قص وتدوير وتجربة، وممكن يبقى عنده
   transient غير حاد.
2. **الترخيص والـQA**: لازم تفتح الترخيص وتذكر المصدر، وتسمع كل ملف قبل ما تستخدمه.

عشان كده المكتبة هنا **متولّدة بالكود** (`templates/procedural-reels/sfx.py`): مجانية ١٠٠٪، أوفلاين،
و**حتمية** — نفس الـseed يطلّع نفس العيّنات بالظبط، فأي ميكس يتعمل تاني بنفس النتيجة على أي جهاز.

## الكتالوج | The kit (15 sounds)
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

كل صوت عنده `family` و`gain` أساسي في `CATALOG` — الميكس بيبدأ من الـgain ده، فـ`gain: 1.0` في cue معناها
«بصوته الصح في الميكس»، مش «أعلى حاجة».

## الأوامر | CLI
```bash
python3 tools/sfx_kit.py --list                 # الكتالوج + المدد
python3 tools/sfx_kit.py --bank out/sfx         # WAV لكل صوت (للـeditor أو After Effects)
python3 tools/sfx_kit.py --demo cache/sfx.mp3   # معاينة مسموعة للكتالوج كله + كل الانتقالات
python3 tools/sfx_kit.py --cues cues.json --length 12 --vo vo.wav --out mix.wav
```
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
python3 tools/sfx_kit.py --cues cuts.json --length 55 --vo vo.wav --out out/mix_raw.wav
```
كل cut بيتحوّل لصوته (`wipe` → `whoosh`، `iris` → `pop`، `glitch` → `glitch`…).

## الميكس مع التعليق | Mixing
```python
from sfx import bus, duck, cues_for_transitions   # templates/procedural-reels/sfx.py
cues = cues_for_transitions(cuts, gain=0.9, pan=(0.6, -0.6))
sfx_bus = bus(55.0, cues)
sfx_bus = duck(vo_mono, sfx_bus, depth=0.62)      # بيتوتّى تحت الكلام
```
والباقي زي ما هو في `mix.py`: `vo + sfx + bed` → `loudnorm` مرتين → limiter → **−14.5 ±0.3 LUFS، TP ≤ −1.5 dBTP**.
صوت أعلى من كده بيخسر على المنصات، وأوطى بيبان ضعيف.

## قواعد عملية | Rules that keep it sounding professional
- **hit واحد لكل معنى**: مش كل حاجة بتتحرك ليها صوت.
- **الانتقالات بس اللي بتاخد whoosh/swipe**، والتغيير الحقيقي (scene cut) ياخد `impact` أو `sub` تحته.
- **الـtick/pop** على الأرقام والعناصر، بحد أقصى ~٨ في الثانية، وبيخفّوا تدريجيًا.
- **التوتير**: خلي 0.6–1.2 ثانية بين أي صوتين في نفس العيلة.
- **التجربة على موبايل**: speakers صغيرة بتخفي `sub`؛ متعتمدش عليه لوحده.
- الأصوات كلها mono عدا الـpan؛ متحطّش reverb جاهز — `noise` يعمل air كفاية.

## إضافة صوت جديد | Adding one
```python
def tape_stop(seed=0):
    """..."""
    ...
BANK["tape_stop"] = tape_stop
CATALOG["tape_stop"] = dict(family="texture", gain=0.4, tags="pause, rewind")
```
وبعدها `tests/test_sfx.py` بيتأكد من الحتمية والمدى والكتالوج، ولو ربطته بانتقال: حط اسمه في
`motion/transitions.json` → `sfx`.
