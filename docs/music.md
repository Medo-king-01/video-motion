# الموسيقى والميكس | Music & the audio mix

موسيقى خلفية **متولّدة بالكود**: أوفلاين، حتمية، وقابلة للتحكم بالكامل — مفيش ملفات صوتية في الريبو
ولا أي خدمة/موديل خارجي. نفس الـseed بيطلّع نفس العيّنات بالظبط، على 44.1kHz أو 48kHz.

```
music-presets.json ──► music.py ──┐
                                   ├──► audio_mix.py ──► out/final_audio.wav ──► ffmpeg mux
sfx.py (20 sounds) ───────────────┤        ▲
voice-over (WAV) ─────────────────┘        │
                                    audio_engine.py (DSP: filters, envelopes, ducking,
                                                     reverb, limiter, true-peak, WAV I/O)
```

## المعمارية | Architecture

| الملف | الدور |
|---|---|
| `medo-motion/templates/procedural-reels/audio_engine.py` | نواة DSP مشتركة. كل دالة بتاخد `sr` صريح (مفيش ثابت عام)، الفلاتر بتتقصّ على Nyquist بدل ما تطلع برّه. فيها `duck_gain` و`limiter` و`true_peak` و`sos/filt/lp/hp/bp` و`polyblep_saw` و`reverb(_ir)` و`adsr`/`exp_decay`/`voice_envelope` و`write_wav`/`read_wav_mono`. |
| `medo-motion/motion/music-presets.json` | **بيانات** الموسيقى: الـsections (intro/build/drop/break/outro/stop)، الـscales، والمقاسات الستة (bpm/key/scale/progression/groove/tone/الطبقات). تعديل النغمة أو الـgroove مش محتاج كود. |
| `medo-motion/templates/procedural-reels/music.py` | محرّك الموسيقى: ٨ طبقات مستقلة، توزيع الـsections على البارات، sidechain، snare roll، crash، طبقة الموبايل، والـlimiter. |
| `medo-motion/templates/procedural-reels/sfx.py` | نفس الـ20 مؤثر القديمة + إضافات، بس بمعدل عيّنة حقيقي وanchors وducking مصلَّح. |
| `medo-motion/templates/procedural-reels/audio_mix.py` | **الـtimeline الواحد**: بيقرأ cue sheet، بيحل كل وقت إلى sample، بيرندر الموسيقى + الـSFX + الـVO، بيعمل ducking، وبيمستر. |
| `tools/music_kit.py` | CLI للرندر/المعاينة/الفحص. |
| `tools/audio_mix.py` | CLI للميكس الكامل + الـstems + loudnorm. |
| `tools/sfx_kit.py` | زي ما هو + `--sr` و`--json` و`--anchored` و`--force`. |

الموسيقى القديمة اللي كانت **inline في `mix.py`** (~35 سطر مثبّتة على Am–F–C–G @76) لسه موجودة
ومش متلمسة — `mix.py` شغّال لمشاريعه. الجديد إن بقى في محرّك حقيقي بدل السطور دي.

## المقاسات | The six presets

المقاسات مش «نفس الموسيقى بمستويات مختلفة» — كل واحد ليه **مقام وسلّم وإيقاع وطبقات** مختلفة:

| المقاس | BPM | المقام | الإحساس | الفرق الحقيقي |
|---|---|---|---|---|
| `tech` | 112 | A minor | تقني/إلكتروني | نبضة ١/١٦، pluck ساطع، room قصير |
| `minimal` | 96 | D dorian | بسيط/نظيف | مفيش clap، pad بطيء، مساحة للكلام |
| `corporate` | 104 | C major | مؤسسي | major، نبضة ١/٨، أرپيجيو دافي |
| `energetic` | 124 | E minor | حماسي | سريع، syncopation، clap على كل backbeat |
| `cinematic` | 82 | B phrygian | سينمائي | بطيء، pad عريض وطويل، ثقل بدل الإيقاع |
| `ambient` | 76 | F lydian | هادئ/تركيز | **مفيش درامز خالص**، pads وtextures طويلة |

الشوفة دي متأكَّدة بالكود: `tests/test_music.py::test_presets_differ_musically_not_just_in_volume`
بيفشل لو مقاسين بقوا نفس الترتيب.

## الطبقات | Layers
`kick · clap · hat · bass · pad · pluck · melody · texture` — كل واحدة ليها مستوى مستقل
(`layers` في الـJSON أو `layers={...}` في الكود) وكل واحدة بتترندر في bus لوحدها.

```python
from music import MusicConfig, render_music
cfg = MusicConfig(preset="tech", duration=16.0, bpm=112, key="A", scale="minor",
                  energy=1.2, seed=7, layers={"hat": 0.3, "pad": 0.9})
bed = render_music(cfg)          # (16*44100, 2) float32
```

المستويات **نسبية** لـ`MASTER_GAIN` الثابت — مش تطبيع على أعلى peak. الفرق مهم: لو الطبقات بتتطبّع
على الـpeak، «قلّل الـhats» بيطلّع الـhats أعلى (`test_layers_are_independently_mixable` بيحرس ده).

## الأقسام | Sections
`intro → build → drop → break → outro`، و`stop` للسكوت المقصود. النِسب بتتحول لبارات كاملة
(فالقطع في المونتاج بيقع على حدّ بار مش في نص جملة)، ولو المدة مش كفاية للأقسام كلها بتُحذف
**الأقل وزنًا** — الـ`drop` ما بيتشالش أبدًا.

```python
MusicConfig(duration=8.0, sections=[{"name": "drop", "start": 0, "end": 3},
                                   {"name": "stop", "start": 3, "end": 4},
                                   {"name": "drop", "start": 4, "end": 8}])
```
الـ`stop` سكوت **حقيقي** (peak = 0) بحدود 4ms cosine — والـgate بيتطبق بعد الـreverb عشان ذيل
الـpad ما يسربش جوّه السكوت.

## التحكم الكامل | Controls
| المتحكم | في الكود | في الـCLI |
|---|---|---|
| المدة | `duration` | `--duration` |
| السرعة | `bpm` | `--bpm` |
| المقام/السلّم | `key`, `scale` | `--key --scale` |
| المزاج (يُسجَّل) | `mood` | `--mood` |
| الطاقة | `energy` (0–2) | `--energy` |
| الـseed | `seed` | `--seed` |
| نسب الأقسام | `sections` | `--intro --build --drop --break --outro` أو `--sections` |
| طبقة | `layers={"hat":0}` | `--layer hat=0` |
| عرض الستيريو | — | `--width 0..2` |
| الـswing | `swings` (0–0.3) | `--swing` |
| معدل العيّنة | `sr` | `--sr 44100/48000` |

## الـCLI
```bash
python3 tools/music_kit.py --presets                       # المقاسات والفرق بينها
python3 tools/music_kit.py --render out/bed.wav --preset cinematic --duration 20 --sr 48000
python3 tools/music_kit.py --preview cache/music-demo.mp3  # يسمّعك الستة ورا بعض
python3 tools/music_kit.py --info --preset energetic       # JSON: بارات/أقسام/طبقات (من غير رندر)
python3 tools/music_kit.py --validate                      # البيانات + كل مقاس بيترندر سليم
```

## الميكس الكامل من timeline واحد | One cue sheet
```json
{"version": 1, "duration": 24.0, "sr": 44100, "seed": 7, "voice": "out/vo.wav",
 "music": {"preset": "tech", "bpm": 112, "key": "A", "scale": "minor", "level_db": -4.0,
           "changes": [{"t": 12.0, "preset": "cinematic", "why": "الفصل التاني"}],
           "duck": {"amount": 0.62, "attack": 0.008, "release": 0.32, "lookahead": 0.04}},
 "sfx": [{"t": 6.4, "sfx": "whoosh", "gain": 0.9, "pan": [-0.6, 0.6], "anchor": true,
          "why": "transition wipe"},
         {"t": 12.0, "sfx": "impact", "gain": 1.0}],
 "duck": {"amount": 0.7, "attack": 0.01, "release": 0.25},
 "master": {"lufs": -14.5, "true_peak": -1.5}}
```

```bash
python3 tools/audio_mix.py --sheet cues.json --dry-run              # الـtimeline ككلام مقروء
python3 tools/audio_mix.py --sheet cues.json --vo out/vo.wav \
        --out out/final_audio.wav --stems out/stems --report out/audio-report.json
python3 tools/audio_mix.py --from-cuts cuts.json --preset tech --duration 24 --out out/mix.wav
```

- **`t` لكل cue = لحظة الحدث** لو `anchor: true` (الـriser ذروته عند `t`، الـwhoosh متوسّط على القطع).
- **`changes`**: كل تغيير موسيقى بيبدأ مقاس جديد من عند الوقت ده (مش بيتطوّل عشان بار).
- **`duck`** على مستوى الـsheet للـSFX، و`music.duck` للموسيقى — الاتنين ليهم `amount`/`attack`/`release`/`lookahead`.
- **`level_db`**: مستوى الموسيقى في الميكس (−3 لو مش مكتوب؛ −6/−8 لو الكلام كتير).
  المقاسات الستة **متساوية في المستوى** (كل واحد عنده `levelTrimDb` مقاس يجيبه على ‎−19 dBFS RMS)،
  فتبديل المقاس مش بيرفع أو يوطّي الموسيقى؛ الـ`level_db` هو اللي بيتحكم في المستوى.
- **تغيير الموسيقى** بيتعمل بـcross-fade 0.45 ثانية: المقاس الجديد بيبدأ قبل التغيير بـ0.45 ث وبيدخل
  بكامل مستواه عند اللحظة (لو دخّلناه بـfade-in، القطع بيبان كأنه فتحة سكوت — ده كان عيب مقاس).
- **`--stems`**: بيطلّع `music.wav` و`sfx.wav` و`vo.wav` منفصلين للمراجعة.
- **`--dry-run`**: بيطبع الـtimeline (الموسيقى + كل cue + السبب) قبل ما ترندر.

### الماستر | Mastering
الأداة بتعمل `loudnorm` على مرحلتين على **−14.5 LUFS / −1.5 dBTP**، وبعدها **بتقيس بمقياس EBU R128
المرجعي** (`ebur128`) وتظبط الفرق بترم بحد أقصى ±2dB، وبتعيد القياس. السبب إن `loudnorm` و`ebur128`
مش متفقين على نفس الملف: على ماستر حقيقي من هنا `loudnorm` قال ‎−14.51 LUFS و`ebur128` قال ‎−14.8.
التقرير بينشر رقم `ebur128` — ده الرقم اللي المنصات هتحسبه.

الترم بيخضع للسقف: لو الترم لفوق هيعدّي ‎−1.5 dBTP، بيتقصّر (الـloudness بيخسر للـceiling).
لو ffmpeg مش موجود، بترجع لنورملالايزر المكتبة (RMS + limiter) وبتقول ده في التقرير بدل ما تسكت.

القياس بيتعمل على الملف اللي اتكتب فعلًا بـ`true_peak` (مش sample peak) — بعد ما اتصلّح عيبين:
`true_peak` كان بياخد `max(axis=1)` فبيرجّع 0 لمادة ستيريو متناظرة، وكان بيقرأ أعلى من الحقيقة بـ1.1dB
على إشارة واقفة لحد آخر عيّنة (الـoversampling بيفترض سكوت بعد الملف).

## الربط بالريندر | Integration with the renderer
الـpipeline القديم زي ما هو (`mix.py` → `out/final_audio.wav`). للمشاريع الجديدة:

```bash
python3 tools/audio_mix.py --from-cuts out/cuts.json --preset tech --vo out/vo.wav \
        --out out/final_audio.wav --force
ffmpeg -i out/video.mp4 -i out/final_audio.wav -c:v copy -c:a aac -b:a 192k -shortest out/final.mp4
```
`--from-cuts` بيقرأ `cuts.json` (قائمة المشاهد/الانتقالات) ويحوّل كل انتقال لصوته من
`motion/transitions.json`، فالصوت بيمشي مع الصورة من نفس المصدر.

## المخرجات | Outputs
| الملف | إيه فيه |
|---|---|
| `out/final_audio.wav` | الميكس النهائي: 44.1k أو 48k، ستيريو، PCM16 |
| `out/stems/{music,sfx,vo}.wav` | نفس الميكس مفكوك — للمراجعة أو لإعادة الميكس |
| `out/audio-report.json` | المدد، الـsegments، الـcues، الـloudnorm المقاس، true peak، أي samples اتقصّت |
| `cache/music-demo.mp3` | معاينة المقاسات الستة ورا بعض |

## استكشاف الأخطاء | Troubleshooting
| الأعراض | السبب | الحل |
|---|---|---|
| الموسيقى مش مسموعة خالص | `level_db` واطي جدًا أو الـpreset كله layers=0 | `--info` واتأكد إن في layers > 0 |
| الصوت بيتقطع في الآخر | cue بعد نهاية الملف | `sfx.truncated_samples > 0` في التقرير |
| riser بيبان مقصوص من الأول | cue متحرك لقدام (onset قبل 0) | ده مقصود — `sfx.early_clipped_samples` |
| الـimpact مش على القطع | `anchor` مش متفعل | حط `"anchor": true` على الـcue |
| الكلام بيغرق في الموسيقى | الـduck قليل | زوّد `music.duck.amount` لـ0.7 وقلّل `level_db` |
| الملف مش −14.5 LUFS | مفيش ffmpeg | نصّب ffmpeg أو اقبل نورملالايزر المكتبة (بيتقاس في التقرير) |
| `FileExistsError` | حماية من الكتابة فوق ملف | `--force` |
| ريندر بطيء | مدة طويلة + reverb | 30 ثانية ≈ 3–4 ثواني رندر على جهاز عادي |

## مثال كامل | One full example
```bash
# 1) التعليق
python3 medo-motion/scripts/build_vo.py --text script.txt --out out/vo.wav

# 2) الـtimeline
python3 - <<'EOF'
import json
json.dump({"duration": 24.0, "sr": 44100, "seed": 11,
  "music": {"preset": "corporate", "level_db": -5.0,
            "changes": [{"t": 14.0, "preset": "cinematic"}]},
  "sfx": [{"t": 1.2, "sfx": "pop"}, {"t": 6.4, "sfx": "whoosh", "anchor": True},
          {"t": 14.0, "sfx": "impact"}, {"t": 14.05, "sfx": "chime", "gain": 0.6}],
  "duck": {"amount": 0.68, "attack": 0.01, "release": 0.28}}, open("out/cues.json", "w"), indent=1)
EOF

# 3) الميكس
python3 tools/audio_mix.py --sheet out/cues.json --vo out/vo.wav \
        --out out/final_audio.wav --stems out/stems --report out/audio-report.json --force

# 4) المونتاج
ffmpeg -i out/video.mp4 -i out/final_audio.wav -c:v copy -c:a aac -b:a 192k -shortest out/final.mp4
```

## الحدود المعروفة | Known limits
- الموسيقى **غربية المقام** (minor/major/dorian/phrygian/lydian/pentatonic). مقامات شرقية (بياتي/حجاز)
  مش مضافة — الـ`scales` في الـJSON بتقبل أي سلّم، فإضافتها سطرين.
- مفيش غنا/كلام في الموسيقى (مقصود: الريل بيحكي هو).
- الـ`melody` بسيطة (سطر من الأرباع)؛ المحرّك مش بديل لملحّن.
- الرندر أسرع من الوقت الحقيقي بكتير بس مش فوري: 30 ثانية ≈ 3–4 ثواني.

## الترخيص | Licence
الأفكار والبنية متأثرة بـ`majedphotos/video-ad-editor` (`motion/audio.py`، MIT © 2026 Majed Alzaabi)،
لكن الكود هنا **مكتوب من جديد** بـNumPy/SciPy على واجهة المشروع ده (معدلات مرنة، anchors،
cue sheet واحد، توافق للخلف مع `sfx.py`). الإسناد في `assets/CREDITS.md`، والتحليل الكامل في
`docs/audio-engine-audit.md`.
