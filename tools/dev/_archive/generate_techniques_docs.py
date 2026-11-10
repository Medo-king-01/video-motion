#!/usr/bin/env python3
"""
توليد توثيق techniques.md من المكتبة المحدثة.
يتضمن التقنيات الأصلية + تقنيات مكتبة Alansari.
"""
import json
import sys
from pathlib import Path

TECHNIQUES_PATH = Path('/home/user/video-motion/assets/techniques.json')
OUTPUT_PATH = Path('/home/user/video-motion/docs/techniques.md')

# خريطة أسماء الفئات بالعربية والإنجليزية
CATEGORY_NAMES = {
    'opening_hook': ('Opening Hook', 'خطافات البداية'),
    'typography': ('Typography', 'الخطوط والطباعة'),
    'transition': ('Transitions', 'الانتقالات'),
    'camera': ('Camera', 'الكاميرا'),
    'depth': ('Depth & 3D', 'العمق والثلاثي الأبعاد'),
    'pacing': ('Pacing', 'الإيقاع'),
    'sound': ('Sound', 'الصوت'),
    'finish': ('Finish', 'اللمسات الأخيرة'),
    'ui_choreography': ('UI Choreography', 'حركة الواجهات'),
    'product_demo': ('Product Demo', 'عروض المنتج'),
    'data_and_numbers': ('Data & Numbers', 'البيانات والأرقام'),
    'micro_interaction': ('Micro Interaction', 'التفاعلات الصغيرة'),
    'layout': ('Layout', 'التخطيط'),
    # الفئات الجديدة من Alansari
    'txt': ('Text In', 'دخول النصوص'),
    'emp': ('Emphasis', 'الإبراز'),
    'cap': ('Captions', 'الكابشن'),
    'trn': ('Transitions (Alansari)', 'الانتقالات'),
    'cam': ('Camera (Alansari)', 'الكاميرا'),
    'fx': ('Effects', 'المؤثرات'),
    'soc': ('Social', 'السوشال'),
    'lgo': ('Logos & Titles', 'الشعارات والعناوين'),
    'per': ('Person FX', 'تأثيرات الشخص'),
    'aud': ('Audio & Beat', 'الصوت والإيقاع'),
    'scr': ('Screens & UI', 'الشاشات والواجهات'),
    'trk': ('Tracking', 'تتبع الحركة'),
    'd3': ('3D (Alansari)', 'الثلاثي الأبعاد'),
    'tim': ('Time FX', 'تأثيرات الوقت'),
}

def generate_markdown():
    """توليد توثيق markdown."""
    with open(TECHNIQUES_PATH, encoding='utf-8') as f:
        data = json.load(f)
    
    techniques = data['techniques']
    
    # تجميع حسب الفئة
    from collections import defaultdict
    by_category = defaultdict(list)
    for tech in techniques:
        by_category[tech['category']].append(tech)
    
    # بناء markdown
    lines = []
    lines.append('# Technique library')
    lines.append('')
    studio_count = len([tech for tech in techniques if not tech.get('source')])
    lines.append(f'**{len(techniques)} techniques** — {studio_count} original studio techniques + the Alansari, Opus and gl-transitions libraries.')
    lines.append('')
    lines.append('Draw a plan with `python3 tools/techniques.py --draw --from-plan plan/beats.json`.')
    lines.append('This page is generated from `assets/techniques.json`, so edit the JSON, not this file.')
    lines.append('')
    
    # ترتيب الفئات
    category_order = [
        'opening_hook', 'typography', 'transition', 'camera', 'depth',
        'pacing', 'sound', 'finish', 'ui_choreography', 'product_demo',
        'data_and_numbers', 'micro_interaction', 'layout',
        'txt', 'emp', 'cap', 'trn', 'cam', 'fx', 'soc', 'lgo',
        'per', 'aud', 'scr', 'trk', 'd3', 'tim'
    ]
    
    # قسم التقنيات الأصلية
    lines.append('---')
    lines.append('')
    lines.append('## 🎬 Studio Techniques (Original)')
    lines.append('')
    lines.append('59 hand-crafted techniques with full studio integration.')
    lines.append('')
    
    for cat in category_order[:13]:  # الفئات الأصلية
        if cat not in by_category:
            continue
        cat_techs = by_category[cat]
        names = CATEGORY_NAMES.get(cat, (cat, cat))
        lines.append(f'### {names[0]} ({names[1]})')
        lines.append('')
        
        for tech in cat_techs:
            tech_id = tech['id']
            name = tech['name']
            role = tech.get('role', 'workhorse')
            energy = tech.get('energy', 'any')
            primitive = tech.get('primitive', 'composite')
            evidence = tech.get('evidence', 0)
            timing = tech.get('timing', '')
            summary = tech.get('summary', '')
            how = tech.get('how', '')
            use_when = tech.get('use_when', '')
            avoid_when = tech.get('avoid_when', '')
            
            lines.append(f'#### `{tech_id}` — {name}')
            lines.append('')
            meta_parts = [role, energy, primitive]
            if evidence:
                meta_parts.append(f'evidence {evidence}')
            if timing:
                meta_parts.append(timing)
            lines.append(f'*{" · ".join(meta_parts)}*')
            lines.append('')
            lines.append(summary)
            lines.append('')
            if how:
                lines.append(f'**How:** {how}')
                lines.append('')
            if use_when:
                lines.append(f'**Use when:** {use_when}')
                lines.append('')
            if avoid_when:
                lines.append(f'**Avoid when:** {avoid_when}')
                lines.append('')
    
    # قسم تقنيات Alansari
    lines.append('---')
    lines.append('')
    lines.append('## 🎨 Alansari Motion Library (Integrated)')
    lines.append('')
    lines.append('275 motions from [Alansari Motion Library](https://github.com/alansariteach/motion-library) — adapted for this studio.')
    lines.append('Each motion has an Arabic and English description, with easing and timing specs.')
    lines.append('')
    
    for cat in category_order[13:]:  # فئات Alansari
        if cat not in by_category:
            continue
        cat_techs = by_category[cat]
        names = CATEGORY_NAMES.get(cat, (cat, cat))
        lines.append(f'### {names[0]} ({names[1]}) — {len(cat_techs)} motions')
        lines.append('')
        
        for tech in cat_techs:
            tech_id = tech['id']
            name = tech.get('name', '')
            name_ar = tech.get('name_ar', name)
            role = tech.get('role', 'workhorse')
            energy = tech.get('energy', 'any')
            primitive = tech.get('primitive', 'composite')
            easing = tech.get('easing', '')
            timing = tech.get('timing', '')
            summary = tech.get('summary', '')
            how = tech.get('how', '')
            how_ar = tech.get('how_ar', '')
            use_when = tech.get('use_when', '')
            use_when_ar = tech.get('use_when_ar', '')
            original_id = tech.get('original_id', '')
            
            lines.append(f'#### `{tech_id}` — {name}')
            if name_ar and name_ar != name:
                lines.append(f'**{name_ar}**')
            lines.append('')
            meta_parts = [role, energy, primitive]
            if easing:
                meta_parts.append(f'easing: {easing}')
            if timing:
                meta_parts.append(timing)
            lines.append(f'*{" · ".join(meta_parts)}*')
            lines.append('')
            if original_id:
                lines.append(f'*Original: {original_id}*')
                lines.append('')
            if summary:
                lines.append(summary)
                lines.append('')
            if how:
                lines.append(f'**Spec (EN):** {how}')
                lines.append('')
            if how_ar:
                lines.append(f'**Spec (AR):** {how_ar}')
                lines.append('')
            if use_when or use_when_ar:
                lines.append('**When to use:**')
                if use_when:
                    lines.append(f'- EN: {use_when}')
                if use_when_ar:
                    lines.append(f'- AR: {use_when_ar}')
                lines.append('')
    
    # كتابة الملف
    content = '\n'.join(lines)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'✅ تم توليد التوثيق: {OUTPUT_PATH}')
    print(f'   {len(techniques)} تقنية في {len(by_category)} فئات')
    
    return 0

if __name__ == '__main__':
    sys.exit(generate_markdown())
