#!/usr/bin/env python3
"""
دمج Opus Motion Library في الاستيديو.
- 616 تقنية جديدة
- 97 انتقال
- 148 ستايل بصري
"""
import json
from pathlib import Path
from collections import Counter

# تحميل ملفات Opus
OPUS_DIR = Path('/tmp/opus-motion-library')
with open(OPUS_DIR / 'catalog.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)
with open(OPUS_DIR / 'styles.json', 'r', encoding='utf-8') as f:
    opus_styles = json.load(f)

# تحميل استيديو
STUDIO_PATH = Path('/home/user/video-motion/assets/techniques.json')
with open(STUDIO_PATH, 'r', encoding='utf-8') as f:
    studio_data = json.load(f)

# خريطة primitive
PRIMITIVE_MAP = {
    'text': 'type',
    'data': 'timeline',
    'ui': 'timeline',
    'fx': 'timeline',
    'environment': 'camera',
    '3d': 'depth',
    'shape': 'timeline',
    'hud': 'timeline',
    'image': 'timeline',
    'game': 'timeline',
    'music': 'sound',
    'product': 'timeline',
    'character': 'timeline',
    'document': 'timeline',
    'map': 'timeline',
    'mascot': 'timeline',
    'camera': 'camera',
    'texture': 'blur',
    'transition': 'transition',
}

ENERGY_MAP = {
    'high': 'high',
    'medium': 'medium',
    'low': 'calm',
}

def convert_opus_motion(motion, index):
    """تحويل حركة Opus إلى تقنية."""
    motion_id = motion.get('id', f'opus-{index}')
    title = motion.get('title', 'Unknown')
    category = motion.get('category', 'fx')
    description = motion.get('description', '')
    use_for = motion.get('useFor', '')
    tags = motion.get('tags', [])
    
    # بناء التقنية
    technique = {
        'id': f'opus-{motion_id}',
        'name': title,
        'name_ar': title,  # Opus بالإنجليزية
        'category': category,
        'role': 'accent',
        'energy': 'any',
        'primitive': PRIMITIVE_MAP.get(category, 'timeline'),
        'summary': description[:200] if description else title,
        'how': description,
        'how_ar': '',
        'timing': f'{motion.get("durationInFrames", 90)} frames @30fps',
        'easing': 'varies',
        'use_when': use_for,
        'use_when_ar': '',
        'avoid_when': '',
        'bans': [],
        'evidence': 0,
        'source': 'opus-motion-library',
        'original_id': motion_id,
        'tags': tags,
        'file': motion.get('file', ''),
        'overlay': motion.get('overlay', False),
    }
    
    return technique

# تحويل حركات Opus
print(f'📥 تحويل {len(catalog)} حركة من Opus...')
new_techniques = []
existing_ids = {t['id'] for t in studio_data['techniques']}

for i, motion in enumerate(catalog):
    try:
        tech = convert_opus_motion(motion, i)
        if tech['id'] not in existing_ids:
            new_techniques.append(tech)
            existing_ids.add(tech['id'])
    except Exception as e:
        print(f'  ⚠️  خطأ في {motion.get("id", i)}: {e}')

print(f'  ✅ تم تحويل {len(new_techniques)} حركة')

# إحصائيات
cats = Counter(t['category'] for t in new_techniques)
print(f'\n📊 حسب الفئة:')
for cat, count in cats.most_common():
    print(f'  {cat}: {count}')

# إضافة للمكتبة
studio_data['techniques'].extend(new_techniques)

# إضافة الفئات الجديدة للفورمات
current_order = studio_data['format']['reel']['order']
new_cats = [c for c in cats.keys() if c not in current_order]
current_order.extend(new_cats)
print(f'\n📂 فئات جديدة: {new_cats}')

# دمج ستايلات Opus (148)
STYLES_PATH = Path('/home/user/video-motion/assets/styles/styles.json')
with open(STYLES_PATH, 'r', encoding='utf-8') as f:
    styles_data = json.load(f)

print(f'\n🎨 دمج {len(opus_styles)} ستايل من Opus...')
existing_style_ids = set(styles_data['styles'].keys())
opus_added = 0

for style in opus_styles:
    style_id = style.get('id', '')
    if style_id not in existing_style_ids:
        # تحويل الستايل
        converted = {
            'name': style.get('name', style_id),
            'name_en': style.get('name', style_id),
            'desc': style.get('description', ''),
            'family': style.get('family', 'custom'),
            'palette': style.get('palette', {}),
            'useFor': style.get('useFor', ''),
            'personality': 'clean',
            'cues': style.get('tags', []),
            'source': 'opus-motion-library',
        }
        styles_data['styles'][style_id] = converted
        existing_style_ids.add(style_id)
        opus_added += 1

print(f'  ✅ تم إضافة {opus_added} ستايل')

# حفظ الملفات
with open(STUDIO_PATH, 'w', encoding='utf-8') as f:
    json.dump(studio_data, f, indent=2, ensure_ascii=False)

with open(STYLES_PATH, 'w', encoding='utf-8') as f:
    json.dump(styles_data, f, indent=2, ensure_ascii=False)

# الإحصائيات النهائية
print(f'\n📊 الإحصائيات النهائية:')
print(f'   التقنيات: {len(studio_data["techniques"])}')
print(f'   الستايلات: {len(styles_data["styles"])}')
print(f'   الفئات: {len(cats)}')
