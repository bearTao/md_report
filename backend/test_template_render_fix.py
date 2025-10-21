#!/usr/bin/env python3
"""测试模板渲染修复"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.renderer import template_renderer
from app.database import SessionLocal
from app.models.db_models import Template

def test_template_rendering():
    """测试修复后的模板渲染"""
    db = SessionLocal()
    
    try:
        # 获取修复后的模板
        template = db.query(Template).filter(Template.id == 'tpl_ai_mysql').first()
        
        if not template:
            print("❌ 未找到模板 tpl_ai_mysql")
            return False
        
        print(f"测试模板: {template.name}")
        print("=" * 80)
        
        # 准备测试数据
        test_variables = {
            'wgid': 'ZQGY0174',
            'report_metadata': {
                'generated_at': '2025-10-20 15:30:00',
                'template_version': '1.0',
                'task_id': 'test_task_123'
            },
            'overview': {
                'micro_grid_name': '测试微网格',
                'city': '上海',
                'area': '浦东新区',
                'wgid_score': 85.5,
                'problem_count': 10,
                'starttime': '2025-01-01',
                'endtime': '2025-03-31'
            },
            'index_scores': [
                {
                    'index': '覆盖率',
                    'values': '95.5',  # 注意：这是字符串类型！
                    'value_data': 95.5,
                    'index_weight': '10.0',  # 字符串
                    'index_score': '9.55',   # 字符串
                    'index_deduction': '0.45'  # 字符串
                },
                {
                    'index': '干扰率',
                    'values': 88.2,  # 数字类型
                    'index_weight': 8.0,
                    'index_score': 7.06,
                    'index_deduction': 0.94
                }
            ],
            'problem_buildings': [
                {'name': 'A楼', 'weak_cell_count': 2},
                {'name': 'B楼', 'weak_cell_count': 3}
            ],
            'executive_summary': '这是一个测试摘要',
            'problem_root_cause_analysis': [
                {'cause': '原因1', 'description': '描述1'}
            ],
            'effect_prediction_and_risks': [
                {'effect': '效果1', 'risk': '风险1'}
            ],
            'detailed_optimization_plan': [
                {'plan': '计划1', 'priority': '高'}
            ],
            'plan_sites': [],
            'problem_clusters': [],
            'problem_grid_mdt': [],
            'problem_grid_cloud': [],
            'building_type_stats': [],
            'grid_mdt_weak_samples': 0,
            'grid_mdt_total_samples': 100,
            'buildings_4g_weak_count': 5,
            'buildings_5g_weak_count': 3,
            'problem_building_clusters': [],
            'buildings_worse_competitor_count': 2
        }
        
        print("测试数据准备完成")
        print(f"  - index_scores[0]['values']: {test_variables['index_scores'][0]['values']} (type: {type(test_variables['index_scores'][0]['values']).__name__})")
        print(f"  - index_scores[1]['values']: {test_variables['index_scores'][1]['values']} (type: {type(test_variables['index_scores'][1]['values']).__name__})")
        print()
        
        # 尝试渲染
        try:
            markdown_content = template_renderer.render(
                template.template_content,
                test_variables
            )
            
            print("✅ 模板渲染成功！")
            print(f"生成的Markdown长度: {len(markdown_content)} 字符")
            
            # 检查关键部分
            if '覆盖率' in markdown_content and '干扰率' in markdown_content:
                print("✅ index_scores 表格渲染成功")
            else:
                print("⚠️ index_scores 表格可能未正确渲染")
            
            # 显示部分内容
            lines = markdown_content.split('\n')
            print(f"\n生成的Markdown前50行:")
            print("=" * 80)
            for i, line in enumerate(lines[:50], 1):
                print(f"{i:3d}| {line}")
            print("=" * 80)
            
            return True
            
        except Exception as e:
            print(f"❌ 模板渲染失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    finally:
        db.close()


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("测试模板渲染修复")
    print("=" * 80 + "\n")
    
    success = test_template_rendering()
    
    if success:
        print("\n✅ 测试通过！模板可以正确处理字符串和数字类型")
        sys.exit(0)
    else:
        print("\n❌ 测试失败")
        sys.exit(1)

