#!/usr/bin/env python3
"""
دمج حركات مكتبة Alansari في مكتبة تقنيات الاستيديو.
يحول الأوصاف التقنية إلى format techniques.json.
"""
import json
import sys
from pathlib import Path

# تحميل مكتبة Alansari
ALANSARI_PATH = Path('/tmp/motion-library/alansari-motion-library.json')
with open(ALANSARI_PATH, 'r', encoding='utf-8') as f:
    alansari_data = json.load(f)

# تحميل مكتبة الاستيديو الحالية
STUDIO_PATH = Path('/home/user/video-motion/assets/techniques.json')
with open(STUDIO_PATH, 'r', encoding='utf-8') as f:
    studio_data = json.load(f)

# الفئات الجديدة المطلوبة
NEW_CATEGORIES = {
    'caption': 'CAP',      # كابشن
    'social': 'SOC',       # سوشال
    'person_fx': 'PER',    # تأثيرات الشخص
    'tracking': 'TRK',     # تتبع الحركة
    'time_fx': 'TIM',      # تأثيرات الوقت
    'audio': 'AUD',        # صوت وإيقاع
    'effects': 'FX',       # مؤثرات
    '3d': 'D3'             # ثلاثي الأبعاد
}

# خريطة تحويل primitive إلى القيم المقبولة في الاستيديو
PRIMITIVE_MAP = {
    'scale': 'depth',        # تحجيم → عمق
    'rotate': 'depth',       # دوران → عمق
    'translate': 'timeline', # حركة → timeline
    'opacity': 'blur',       # شفافية → blur
    'blur': 'blur',          # ضبابية
    'shake': 'timeline',     # اهتزاز → timeline
    'pulse': 'sound',        # نبض → sound
    'track': 'camera',       # تتبع → camera
    'composite': 'timeline', # مركب → timeline
}

# خريطة تحويل energy إلى القيم المقبولة في الاستيديو
ENERGY_MAP = {
    'low': 'calm',           # منخفض → هادئ
    'medium': 'medium',      # متوسط
    'high': 'high',          # عالي
    'any': 'any',            # أي
}

def determine_role(motion):
    """تحديد دور التقنية (workhorse أو accent)."""
    # الحركات الأساسية = workhorse، المتغيرات = accent
    if motion.get('variant_of'):
        return 'accent'
    return 'workhorse'

def determine_energy(motion):
    """تحديد مستوى الطاقة من easing."""
    easing = motion.get('easing', '').lower()
    if 'bounce' in easing or 'back' in easing:
        return 'high'
    if 'linear' in easing or 'sine' in easing or 'quad' in easing:
        return 'low'
    return 'any'

def determine_primitive(motion):
    """تحديد نوع الحركة الأساسي."""
    spec = motion.get('spec_ar', '').lower()
    if any(w in spec for w in ['تكبير', 'تصغير', 'scale']):
        return 'scale'
    if any(w in spec for w in ['دوران', 'لف', 'rotate', 'spin']):
        return 'rotate'
    if any(w in spec for w in ['تحرك', 'انزلاق', 'slide', 'move']):
        return 'translate'
    if any(w in spec for w in ['شفافية', 'fade', 'opacity']):
        return 'opacity'
    if any(w in spec for w in ['ضبابية', 'blur']):
        return 'blur'
    if any(w in spec for w in ['اهتزاز', 'shake']):
        return 'shake'
    if any(w in spec for w in ['نبض', 'pulse']):
        return 'pulse'
    if any(w in spec for w in ['تتبع', 'track']):
        return 'track'
    return 'composite'

def convert_motion_to_technique(motion, category_mapping):
    """تحويل حركة من مكتبة Alansari إلى تقنية للستوديو."""
    cat_id = motion['category']
    studio_cat = category_mapping.get(cat_id, cat_id.lower())
    
    # بناء المعرف الفريد
    motion_id = motion['id'].lower().replace('m-', '')
    technique_id = f"al-{studio_cat}-{motion_id}"
    
    # بناء الوصف
    name_en = motion.get('name_en', 'Unknown')
    name_ar = motion.get('name_ar', name_en)
    
    # تحديد الأدوار والخصائص
    role = determine_role(motion)
    energy = determine_energy(motion)
    primitive_raw = determine_primitive(motion)
    
    # تحويل القيم إلى القيم المقبولة
    primitive = PRIMITIVE_MAP.get(primitive_raw, 'timeline')
    energy = ENERGY_MAP.get(energy, 'any')
    
    # بناء التقنية
    technique = {
        'id': technique_id,
        'name': name_en,
        'name_ar': name_ar,
        'category': studio_cat,
        'role': role,
        'energy': energy,
        'primitive': primitive,
        'summary': motion.get('when_to_use_en', f'{name_en} motion'),
        'how': motion.get('spec_en', ''),
        'how_ar': motion.get('spec_ar', ''),
        'timing': motion.get('duration', ''),
        'easing': motion.get('easing', ''),
        'use_when': motion.get('when_to_use_en', ''),
        'use_when_ar': motion.get('when_to_use_ar', ''),
        'avoid_when': 'For static cards or when the scene is already busy with multiple elements.',
        'bans': [],
        'evidence': 0,
        'source': 'alansari-motion-library',
        'original_id': motion['id']
    }
    
    # إضافة المحتوى المطلوب
    if motion.get('content_needed'):
        technique['content_needed'] = motion['content_needed']
    
    return technique

def main():
    """الدمج الرئيسي."""
    print(f"📥 تحميل مكتبة Alansari...")
    all_motions = alansari_data['motions']
    print(f"   {len(all_motions)} حركة")
    
    print(f"\n📊 تحميل مكتبة الاستيديو الحالية...")
    existing_count = len(studio_data['techniques'])
    print(f"   {existing_count} تقنية")
    
    # استخراج الحركات الأساسية فقط (بدون المتغيرات)
    base_motions = [m for m in all_motions if not m.get('variant_of')]
    print(f"\n🎯 استخراج الحركات الأساسية...")
    print(f"   {len(base_motions)} حركة أساسية")
    
    # تحويل الحركات
    print(f"\n🔄 تحويل الحركات إلى format الاستيديو...")
    new_techniques = []
    for motion in base_motions:
        try:
            technique = convert_motion_to_technique(motion, NEW_CATEGORIES)
            new_techniques.append(technique)
        except Exception as e:
            print(f"   ⚠️  خطأ في {motion['id']}: {e}")
    
    print(f"   ✅ تم تحويل {len(new_techniques)} تقنية")
    
    # إحصائيات حسب الفئة
    from collections import Counter
    cat_counts = Counter(t['category'] for t in new_techniques)
    print(f"\n📈 التقنيات الجديدة حسب الفئة:")
    for cat, count in sorted(cat_counts.items()):
        print(f"   {cat}: {count}")
    
    # دمج مع المكتبة الحالية
    print(f"\n🔀 دمج التقنيات...")
    existing_ids = {t['id'] for t in studio_data['techniques']}
    merged_count = 0
    for tech in new_techniques:
        if tech['id'] not in existing_ids:
            studio_data['techniques'].append(tech)
            existing_ids.add(tech['id'])
            merged_count += 1
    
    print(f"   ✅ تم دمج {merged_count} تقنية جديدة")
    
    # حفظ النتيجة
    print(f"\n💾 حفظ المكتبة المحدثة...")
    with open(STUDIO_PATH, 'w', encoding='utf-8') as f:
        json.dump(studio_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ تم الحفظ في {STUDIO_PATH}")
    print(f"\n📊 الإحصائيات النهائية:")
    print(f"   التقنيات الأصلية: {existing_count}")
    print(f"   التقنيات المضافة: {merged_count}")
    print(f"   الإجمالي: {len(studio_data['techniques'])}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
