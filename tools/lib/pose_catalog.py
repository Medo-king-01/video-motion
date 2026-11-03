"""The pose catalogue: what the presenter library *is*, independent of the files on disk.

Kept apart from `pose_library.py` (which reads, cuts and writes files) so the naming, the Arabic
labels and the English search words can be reviewed and extended without touching the pipeline.

`en` is the stable English search word an agent matches a scene against; `ar` is the label shown to
a human; `tags` feed the "which pose fits this beat" search. **A pose that is not in this catalogue
is not in the library** — and a scene that needs a pose the library does not have is a reason to ask
the user for it (AGENTS.md §1), never to invent one or reuse a wrong one.

Source: Medo's personal pose library (github.com/Medo-king-01/Medo-s-Personal-Library) — 49 RGBA
cut-outs of one character: 30 full-body and 19 half-body. `SOURCE_ID` records which file each slug
came from, so the import can be re-run and verified instead of guessed.
"""
from __future__ import annotations

# The two framings the engines place differently:
#   full — figure height normalised, soles on the ground line → wide/medium shot
#   bust — cut-out normalised by image height, hair on the top guide → close-up
# Cutting between them reads as a camera push-in, which is exactly what these two sets are for.
FRAMING = {"full": {"height": 1200, "place": "feet"}, "bust": {"height": 1180, "place": "top"}}

# Presented order: the everyday beats first, then motion, interaction, and the half-body set.
# (slug, Arabic label, English search word, tags, facing, note)
POSES: tuple[tuple[str, str, str, tuple[str, ...], str, str], ...] = (
    # ---- standing: the base beats ----
    ("neutral", "وقوف ثابت", "neutral", ("standing", "idle"), "front", "وضعية الأساس — وقوف بثقة"),
    ("arms-crossed", "دراعين متقاطعين", "arms-crossed", ("standing", "closed", "assertive"), "front", "دراعين متقاطعين — رأي أو موقف"),
    ("smile-calm", "ابتسامة هادئة", "smile", ("standing", "calm", "smile"), "front", "ابتسامة هادية — جملة ودّية"),
    ("open-hands", "إيماءة مفتوحة", "open-hands", ("standing", "talk", "hands"), "front", "إيدين مفتوحين — بيفسّر فكرة"),
    ("explain", "بيقدّم معلومة", "explaining", ("standing", "talk", "direct"), "front", "شرح مباشر للكاميرا"),
    ("point", "بيشاور وهو بيتكلم", "pointing", ("standing", "direct"), "front", "إشارة أثناء الحديث — توجيه الانتباه"),
    ("point-viewer", "بيشاور على المشاهد", "point-viewer", ("standing", "direct", "you"), "front", "إشارة للكاميرا — «إنت»"),
    ("point-up", "بيشاور لفوق", "point-up", ("standing", "direct", "emphasis"), "front", "إصبع لفوق — تأكيد نقطة"),
    ("welcome", "الترحيب", "welcome", ("standing", "open-arms", "greeting"), "front", "الدراعين مفتوحين — افتتاحية"),
    ("wave", "التلويح", "wave", ("standing", "greeting"), "front", "إيد مرفوعة — ترحيب أو وداع"),
    ("wave-goodbye", "تلويح بالوداع", "goodbye", ("standing", "greeting", "closing"), "front", "وداع — خاتمة الريل"),
    ("clap", "التصفيق", "clapping", ("standing", "celebration"), "front", "إيدين متقابلين — تصفيق"),
    ("clap-excited", "تصفيق بحماس", "clap-excited", ("standing", "celebration", "high"), "front", "تصفيق بحماس — لحظة نجاح"),
    ("celebrate", "احتفال بإنجاز", "celebrating", ("standing", "celebration", "high"), "front", "احتفال — إنجاز اتحقق"),
    ("like", "إبهام مرفوع", "thumbs-up", ("standing", "approval", "smile"), "front", "إبهام مرفوع — موافقة"),
    ("discovery", "اكتشاف أمر جديد", "discovering", ("standing", "surprise", "idea"), "front", "لحظة اكتشاف — فكرة ظهرت"),
    ("confused-choice", "التردد بين خيارين", "choosing", ("standing", "question", "choice"), "front", "تردد بين اختيارين — مقارنة"),
    ("thinking", "تفكير متأمل", "thinking", ("standing", "pause"), "front", "تفكير هادي — لحظة تأمل"),
    ("think-hands", "تفكير ودراعين متشابكين", "thinking-arms", ("standing", "pause", "closed"), "front", "دراعين متشابكين — تفكير عميق"),
    ("sad", "وقفة حزينة", "sad", ("standing", "down", "low"), "front", "وقفة حزينة — مشكلة أو خسارة"),
    ("shocked", "الصدمة", "shocked", ("standing", "impact", "wide"), "front", "صدمة — لحظة impact"),
    ("surprised", "الانبهار والدهشة", "surprised", ("standing", "impact", "wow"), "front", "دهشة — معلومة مفاجئة"),
    ("warning", "تحذير بإصبع مرفوع", "warning", ("standing", "direct", "caution"), "front", "إصبع تحذيري — تنبيه"),
    # ---- motion ----
    ("walk", "المشي إلى اليسار", "walking", ("motion", "side"), "left", "مشي جانبي — انتقال أو loop"),
    ("run", "الركض", "running", ("motion", "side", "fast"), "left", "جري — إلحاح أو سرعة"),
    # ---- seated ----
    ("seated-talk", "قاعد على كرسي", "seated-talk", ("sitting", "chair", "talk"), "front", "قاعد — كلام هادي"),
    ("seated-reflect", "التأمل على مقعد", "seated-reflect", ("sitting", "seat", "pause"), "front", "قاعد متأمل — تفكير طويل"),
    # ---- props & interaction ----
    ("laptop-work", "العمل على لابتوب", "laptop", ("sitting", "device", "tech"), "front", "بيشتغل على لابتوب — سياق تقني"),
    ("phone", "موبايل واقف", "phone", ("standing", "device", "tech"), "front", "بيستخدم الموبايل — سياق موبايل"),
    ("document", "قراءة ورقة", "document", ("standing", "document"), "front", "ماسك ورقة — سكريبت أو عقد"),
    # ---- half body: the close framing ----
    ("angry", "الغضب بقبضتين", "angry", ("bust", "impact", "strong"), "front", "قبضتين مشدودتين — غضب"),
    ("hide-face", "إخفاء الوجه باليد", "facepalm", ("bust", "reaction", "low"), "front", "كف على الوش — «يا نهار»"),
    ("laptop-hold", "حمل اللابتوب", "laptop-hold", ("bust", "device", "tech"), "front", "شايل لابتوب — منتج أو جهاز"),
    ("listen", "الإنصات بانتباه", "listening", ("bust", "attention", "calm"), "front", "إنصات — «دقيقة واحدة»"),
    ("shh", "إشارة الصمت", "shh", ("bust", "quiet", "secret"), "front", "إصبع على البق — سر أو صمت"),
    ("point-self", "الإشارة إلى النفس", "point-self", ("bust", "personal"), "front", "إشارة للنفس — «أنا»"),
    ("point-down", "الإشارة إلى الأسفل", "point-down", ("bust", "direct", "detail"), "front", "إشارة لتحت — تفصيلة على الشاشة"),
    ("point-aside", "الإشارة إلى الجانب", "point-aside", ("bust", "direct", "side"), "front", "إشارة للجانب — جنب عنصر"),
    ("relaxed", "الاسترخاء بابتسامة", "relaxed", ("bust", "calm", "smile"), "front", "جسم مرتاح — إيقاع هادي"),
    ("searching", "البحث عن شيء بعيد", "searching", ("bust", "question", "distance"), "front", "بص بعيد — «فين الحل؟»"),
    ("shrug", "رفع الكتفين بحيرة", "shrug", ("bust", "question", "hands"), "front", "رفع كتفين — «مش عارف»"),
    ("head-scratch", "حك الرأس بحيرة", "head-scratch", ("bust", "question", "pause"), "front", "حك الرأس — تفكير محتار"),
    ("coat-look", "إطلالة بمعطف", "coat", ("bust", "style", "pose"), "front", "وقفة ستايل — لقطة تعريفية"),
    ("watch", "تفقد ساعة اليد", "watch", ("bust", "prop", "time"), "front", "بيبص على الساعة — وقت أو تأخير"),
    ("phone-show", "عرض الهاتف", "phone-show", ("bust", "device", "show"), "front", "بيوري الموبايل — عرض منتج"),
    ("coffee", "حمل كوب القهوة", "coffee", ("bust", "prop", "calm"), "front", "كوب قهوة — لحظة هادية"),
    ("sigh", "الإرهاق", "tired", ("bust", "down", "low"), "front", "إرهاق — «خلاص تعبت»"),
    ("close-explain", "قريب — بيشرح", "close-explaining", ("bust", "talk", "hands"), "front", "لقطة قريبة — شرح بإيد مفتوحة"),
    ("close-thinking", "قريب — بيفكر", "close-thinking", ("bust", "pause"), "front", "لقطة قريبة — إيد على الذقن"),
)

# Which framing each pose belongs to. The 19 half-body images are the close framing; the 30
# full-body ones stand on the ground line.
BUST = frozenset({"angry", "hide-face", "laptop-hold", "listen", "shh", "point-self", "point-down",
                  "point-aside", "relaxed", "searching", "shrug", "head-scratch",
                  "coat-look", "watch", "phone-show", "coffee", "sigh",
                  "close-explain", "close-thinking"})

# A seated pose normalised to the same figure height looks oversized next to a standing one.
SCALE = {"seated-reflect": 0.86, "seated-talk": 0.88, "laptop-work": 0.88, "run": 0.94, "walk": 0.97}

# Which file in the personal library each slug was cut from (provenance + a verifiable re-import).
SOURCE_ID = {
    "neutral": "275b28c0",
    "arms-crossed": "c806effb",
    "open-hands": "82eaf855",
    "explain": "bb6f2319",
    "point": "40648adf",
    "point-viewer": "65f29fe6",
    "point-up": "045ec2ce",
    "welcome": "61cbb7cc",
    "wave": "e43bbc2b",
    "wave-goodbye": "b14b0737",
    "clap": "1ab16f47",
    "clap-excited": "ead0a8d4",
    "celebrate": "86d425a2",
    "like": "b91418ec",
    "discovery": "0e2dca86",
    "confused-choice": "d6d3e96d",
    "thinking": "5eb9d86f",
    "think-hands": "9fa48aec",
    "sad": "185763f2",
    "shocked": "3a6b5bb8",
    "surprised": "bb66a5d6",
    "warning": "bc9e9b3b",
    "walk": "893b37cf",
    "run": "1ea3faf0",
    "seated-talk": "c60069ca",
    "seated-reflect": "3947fbd4",
    "laptop-work": "a024a458",
    "phone": "f6f61347",
    "document": "a43002e7",
    "angry": "5be9f266",
    "hide-face": "8ecb7ffa",
    "laptop-hold": "1b727226",
    "listen": "9e9d1b82",
    "shh": "1ce0a83a",
    "point-self": "81fdaac5",
    "point-down": "69feba61",
    "point-aside": "9c8537aa",
    "relaxed": "364afa9c",
    "smile-calm": "bb795d3a",
    "searching": "81f21884",
    "shrug": "34269578",
    "head-scratch": "1026f467",
    "coat-look": "0d3940a4",
    "watch": "e996ea7e",
    "phone-show": "f7435f58",
    "coffee": "ef5c1319",
    "sigh": "a15799a2",
    "close-explain": "00215f8c",
    "close-thinking": "cd2f564f",
}

# Old scene code — and the previous 24-pose library — used these names; they must keep resolving.
ALIASES = {
    "medo": "neutral", "medo_neutral": "neutral", "medo_wave": "wave", "medo_think": "thinking",
    "medo_thinking": "thinking", "medo_deep": "think-hands", "medo_point": "point",
    "medo_explain": "explain", "medo_welcome": "welcome", "medo_clap": "clap", "medo_like": "like",
    "medo_puzzled": "shrug", "medo_sad": "sad", "medo_shocked": "shocked",
    "medo_walk": "walk", "medo_run": "run",
    # the previous library's slugs → the closest pose in this one, so old scene code keeps working
    "confident-stand": "neutral", "waiting": "neutral", "warm": "open-hands", "puzzled": "shrug",
    "unfold": "document", "thinking-deep": "seated-reflect", "close-neutral": "listen",
    "close-point": "point-aside", "walk-left": "walk", "computer-seated": "laptop-work",
    "tablet-note": "document", "phone-stand": "phone", "wave-calm": "wave", "relaxed-arm": "relaxed",
    # generic search words an agent may try
    "enjoy": "like", "delighted": "like", "cheer": "celebrate", "excited": "clap-excited",
    "open": "open-hands", "greeting": "welcome", "bye": "wave-goodbye", "goodbye": "wave-goodbye",
    "thumbsup": "like", "thumbs_up": "like", "desk": "laptop-work", "sit": "seated-talk",
    "seat": "seated-reflect", "tired": "sigh", "reading": "document", "paper": "document",
    "notebook": "document", "device": "phone", "mobile": "phone", "show-phone": "phone-show",
    "time": "watch", "quiet": "shh", "secret": "shh", "attention": "listen", "angry-shout": "angry",
    "fear": "shocked", "wow": "surprised", "why": "shrug", "confused": "shrug",
    "idle": "neutral", "stand": "neutral", "crossed": "arms-crossed",
}

DEFAULT_POSE = "neutral"


def slugs() -> tuple[str, ...]:
    """Every slug the library can resolve, in presentation order."""
    return tuple(pose[0] for pose in POSES)


def by_slug(slug: str) -> dict | None:
    """The catalogue entry for `slug` (slug, ar, en, tags, facing, note → dict), or None."""
    for pose_slug, ar, en, tags, facing, note in POSES:
        if pose_slug == slug:
            return {"slug": pose_slug, "ar": ar, "en": en, "tags": list(tags),
                    "facing": facing, "note": note}
    return None
