# projects — كل فيديو في فولدر

```bash
python3 tools/new_project.py اسم-المشروع --engine p
```

بيتعمل:

```
projects/اسم-المشروع/
├── BRIEF.md        ← العناصر الأربعة بس: السكريبت · توجيه المشاهد · الصوت · صور ميدو
├── PROGRESS.md     ← مراحل الشغل (intake → beats → prototype → render → mix → QC → delivered)
├── TASTE.md        ← ذوق المشروع (بيبدأ من قيم البراند المقفولة)
├── plan/
│   ├── script.md   ← السكريبت
│   └── beats.json  ← التوقيتات بعد تحليل الصوت
├── assets/
│   ├── vo/         ← صوت التعليق
│   ├── poses/      ← صور ميدو
│   ├── fonts/Cairo/
│   └── sfx/
├── out/            ← chunks + video_only + المعاينة (مش بيترفع على git)
└── cache/
```

بعد الملء قول للوكيل: **«اقرأ AGENTS.md وابدأ»**.

ملاحظات:
- `--engine p` بينسخ محرك Pillow/OpenCV في جذر المشروع (زي `medo-playbook.md` §2).
- `--engine k` بينسخ محرك Canvas/Playwright في `src/`.
- المخرجات (`out/`, `cache/`, `*.mp4`) مستثناة من git — الأعمال الكبيرة متتتبعش.
