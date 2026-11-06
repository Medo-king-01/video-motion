#!/usr/bin/env python3
"""
دمج gl-transitions في الاستيديو.
189 انتقال GLSL جاهز للاستخدام.
"""
import json
import os
import glob
from pathlib import Path

GL_DIR = Path('/tmp/gl-transitions')

# تحميل استيديو
STUDIO_PATH = Path('/home/user/video-motion/assets/techniques.json')
with open(STUDIO_PATH, 'r', encoding='utf-8') as f:
    studio_data = json.load(f)

# استخراج كل انتقالات GLSL
transitions = []
for f in sorted(glob.glob(str(GL_DIR / 'transitions/*.glsl'))):
    name = os.path.basename(f)[:-5]
    with open(f, 'r') as fh:
        glsl = fh.read()
    
    # استخراج uniform params
    uniforms = []
    for line in glsl.split('\n'):
        if 'uniform' in line and not line.strip().startswith('//'):
            uniforms.append(line.strip())
    
    # استخراج الوصف من comments
    desc = ''
    for line in glsl.split('\n'):
        if line.strip().startswith('//') and 'description' in line.lower():
            desc = line.strip().lstrip('/').strip()
            break
    
    transitions.append({
        'id': name,
        'glsl': glsl,
        'uniforms': uniforms,
        'description': desc,
    })

print(f'📥 تحويل {len(transitions)} انتقال GLSL...')

# إضافة كـ techniques
existing_ids = {t['id'] for t in studio_data['techniques']}
new_count = 0

for trans in transitions:
    tech_id = f'gl-{trans["id"].lower()}'
    if tech_id not in existing_ids:
        technique = {
            'id': tech_id,
            'name': trans['id'],
            'name_ar': trans['id'],
            'category': 'gl-transition',
            'role': 'accent',
            'energy': 'any',
            'primitive': 'transition',
            'summary': trans['description'] or f"GLSL transition: {trans['id']}",
            'how': f"GLSL shader with {len(trans['uniforms'])} uniform parameters",
            'how_ar': f'شيدور GLSL بـ {len(trans["uniforms"])} معامل',
            'timing': '0.5s default',
            'easing': 'linear',
            'use_when': 'When you need a GPU-accelerated transition',
            'use_when_ar': 'عند الحاجة لانتقال مدعوم بالمعالج الرسومي',
            'avoid_when': 'When rendering without GPU support',
            'avoid_when_ar': 'عند الرندر بدون دعم GPU',
            'bans': [],
            'evidence': 0,
            'source': 'gl-transitions',
            'glsl_file': f'transitions/{trans["id"]}.glsl',
            'uniforms': trans['uniforms'],
        }
        studio_data['techniques'].append(technique)
        existing_ids.add(tech_id)
        new_count += 1

print(f'  ✅ تم إضافة {new_count} انتقال')

# إضافة الفئة للفورمات
current_order = studio_data['format']['reel']['order']
if 'gl-transition' not in current_order:
    current_order.append('gl-transition')
    print(f'  📂 فئة جديدة: gl-transition')

# حفظ
with open(STUDIO_PATH, 'w', encoding='utf-8') as f:
    json.dump(studio_data, f, indent=2, ensure_ascii=False)

# نسخ ملفات GLSL
DEST_DIR = Path('/home/user/video-motion/assets/gl-transitions')
DEST_DIR.mkdir(parents=True, exist_ok=True)

import shutil
for f in glob.glob(str(GL_DIR / 'transitions/*.glsl')):
    shutil.copy2(f, DEST_DIR)

print(f'  💾 تم نسخ ملفات GLSL إلى assets/gl-transitions/')

# الإحصائيات النهائية
print(f'\n📊 الإحصائيات النهائية:')
print(f'   التقنيات: {len(studio_data["techniques"])}')
print(f'   الفئات: {len(set(t["category"] for t in studio_data["techniques"]))}')
