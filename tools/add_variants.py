#!/usr/bin/env python3
"""
إضافة متغيرات الحركات (Fast/Slow/Gold/Boxed) من مكتبة Alansari.
كل حركة أساسية لها 4 أشكال مختلفة = مرونة أكبر في التصميم.
"""
import json
import sys
from pathlib import Path

# تحميل مكتبة Alansari
ALANSARI_PATH = Path('/tmp/motion-library/alansari-motion-library.json')
with open(ALANSARI_PATH, encoding='utf-8') as f:
    alansari_data = json.load(f)

# تحميل مكتبة الاستيديو الحالية
STUDIO_PATH = Path('/home/user/video-motion/assets/techniques.json')
with open(STUDIO_PATH, encoding='utf-8') as f:
    studio_data = json.load(f)

# خريطة تحويل primitive
PRIMITIVE_MAP = {
    'scale': 'depth',
    'rotate': 'depth',
    'translate': 'timeline',
    'opacity': 'blur',
    'blur': 'blur',
    'shake': 'timeline',
    'pulse': 'sound',
    'track': 'camera',
    'composite': 'timeline',
}

# خريطة تحويل energy
ENERGY_MAP = {
    'low': 'calm',
}

# خريطة أنواع المتغيرات
VARIANT_TYPES = {
    'Fast': {'name_suffix': '· Fast', 'name_ar_suffix': '· سريع', 'speed_factor': 0.6, 'role': 'accent', 'description': 'أسرع بـ 40%'},
    'Slow': {'name_suffix': '· Slow', 'name_ar_suffix': '· بطيء', 'speed_factor': 1.6, 'role': 'accent', 'description': 'أبطأ بـ 60%'},
    'Gold': {'name_suffix': '· Gold', 'name_ar_suffix': '· ذهبي', 'speed_factor': 1.0, 'role': 'accent', 'description': 'نسخة ذهبية فاخرة'},
    'Boxed': {'name_suffix': '· Boxed', 'name_ar_suffix': '· صندوق', 'speed_factor': 1.0, 'role': 'accent', 'description': 'النص داخل صندوق ملون'},
}

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

def determine_energy(motion):
    """تحديد مستوى الطاقة من easing."""
    easing = motion.get('easing', '').lower()
    if 'bounce' in easing or 'back' in easing:
        return 'high'
    if 'linear' in easing or 'sine' in easing or 'quad' in easing:
        return 'low'
    return 'any'

def convert_variant(motion, variant_type):
    """تحويل متغير حركة إلى تقنية للستوديو."""
    cat_id = motion['category'].lower()
    motion_id = motion['id'].lower().replace('m-', '')
    
    # بناء معرف المتغير
    variant_key = variant_type.lower()
    technique_id = f"al-{cat_id}-{motion_id}-{variant_key}"
    
    # بناء الأسماء
    variant_info = VARIANT_TYPES[variant_type]
    name_en = f"{motion.get('name_en', 'Unknown')} {variant_info['name_suffix']}"
    name_ar = f"{motion.get('name_ar', name_en)} {variant_info['name_ar_suffix']}"
    
    # تحديد الخصائص
    primitive_raw = determine_primitive(motion)
    primitive = PRIMITIVE_MAP.get(primitive_raw, 'timeline')
    energy_raw = determine_energy(motion)
    energy = ENERGY_MAP.get(energy_raw, 'any')
    
    # بناء التقنية
    technique = {
        'id': technique_id,
        'name': name_en,
        'name_ar': name_ar,
        'category': cat_id,
        'role': variant_info['role'],
        'energy': energy,
        'primitive': primitive,
        'summary': f"Variant of {motion['id']}: {variant_info['description']}",
        'how': motion.get('spec_en', ''),
        'how_ar': motion.get('spec_ar', ''),
        'timing': motion.get('duration', ''),
        'easing': motion.get('easing', ''),
        'use_when': f"Use when you need a {variant_type.lower()} version of {motion['id']}.",
        'use_when_ar': f"استخدم عندما تحتاج نسخة {variant_info['description']} من {motion['id']}.",
        'avoid_when': 'Same constraints as the base motion.',
        'bans': [],
        'evidence': 0,
        'source': 'alansari-motion-library',
        'original_id': motion['id'],
        'variant_type': variant_type,
        'base_technique': f"al-{cat_id}-{motion_id}"
    }
    
    return technique

def main():
    """الدمج الرئيسي."""
    print("📥 تحميل مكتبة Alansari...")
    all_motions = alansari_data['motions']
    
    # استخراج الحركات الأساسية فقط
    base_motions = [m for m in all_motions if not m.get('variant_of')]
    print(f"   {len(base_motions)} حركة أساسية")
    
    print("\n🔄 توليد المتغيرات...")
    variant_count = 0
    new_techniques = []
    
    for motion in base_motions:
        for variant_type in VARIANT_TYPES.keys():
            try:
                technique = convert_variant(motion, variant_type)
                new_techniques.append(technique)
                variant_count += 1
            except Exception as e:
                print(f"   ⚠️  خطأ في {motion['id']} - {variant_type}: {e}")
    
    print(f"   ✅ تم توليد {variant_count} متغير")
    
    # إحصائيات حسب النوع
    from collections import Counter
    type_counts = Counter(t['variant_type'] for t in new_techniques)
    print("\n📈 المتغيرات حسب النوع:")
    for vtype, count in sorted(type_counts.items()):
        print(f"   {vtype}: {count}")
    
    # دمج مع المكتبة الحالية
    print("\n🔀 دمج المتغيرات...")
    existing_ids = {t['id'] for t in studio_data['techniques']}
    merged_count = 0
    for tech in new_techniques:
        if tech['id'] not in existing_ids:
            studio_data['techniques'].append(tech)
            existing_ids.add(tech['id'])
            merged_count += 1
    
    print(f"   ✅ تم دمج {merged_count} متغير جديد")
    
    # حفظ النتيجة
    print("\n💾 حفظ المكتبة المحدثة...")
    with open(STUDIO_PATH, 'w', encoding='utf-8') as f:
        json.dump(studio_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ تم الحفظ في {STUDIO_PATH}")
    print("\n📊 الإحصائيات النهائية:")
    print(f"   التقنيات قبل: {len(studio_data['techniques']) - merged_count}")
    print(f"   المتغيرات المضافة: {merged_count}")
    print(f"   الإجمالي: {len(studio_data['techniques'])}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
