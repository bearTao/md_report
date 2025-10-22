#!/usr/bin/env python3
"""诊断Vision AI问题的工具"""
import requests
import json

BASE_URL = "http://localhost:8000"

def list_templates():
    """列出所有模板"""
    print("=" * 60)
    print("查找包含 vision_ai 的模板")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/templates/")
    if response.status_code != 200:
        print(f"❌ 获取模板列表失败: {response.status_code}")
        return []
    
    data = response.json()
    templates = data if isinstance(data, list) else data.get('templates', [])
    vision_ai_templates = []
    
    for tpl in templates:
        # 检查metadata中是否有vision_ai类型的变量
        metadata = tpl.get('metadata_json', {})
        has_vision_ai = any(
            var_config.get('source') == 'vision_ai' 
            for var_config in metadata.values()
        )
        
        if has_vision_ai:
            vision_ai_templates.append(tpl)
            print(f"\n📋 模板: {tpl['name']}")
            print(f"   ID: {tpl['id']}")
            print(f"   创建时间: {tpl['created_at']}")
            
            # 显示vision_ai变量配置
            for var_name, var_config in metadata.items():
                if var_config.get('source') == 'vision_ai':
                    print(f"\n   Vision AI变量: {var_name}")
                    vision_config = var_config.get('vision_ai_config', {})
                    print(f"     - image_source: {vision_config.get('image_source')}")
                    print(f"     - model: {vision_config.get('model')}")
                    
                    # 检查关联的image变量
                    image_source = vision_config.get('image_source')
                    if image_source and image_source in metadata:
                        image_config = metadata[image_source].get('image_config', {})
                        print(f"\n   关联Image变量: {image_source}")
                        print(f"     - endpoint: {image_config.get('endpoint')}")
                        print(f"     - output_format: {image_config.get('output_format')}")
    
    return vision_ai_templates

def check_recent_tasks():
    """检查最近的失败任务"""
    print("\n" + "=" * 60)
    print("检查最近的任务")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/reports/?page_size=10")
    if response.status_code != 200:
        print(f"❌ 获取报告列表失败: {response.status_code}")
        return
    
    data = response.json()
    items = data.get('items', [])
    
    for item in items[:5]:  # 只显示最近5个
        status = item.get('status')
        task_id = item.get('task_id')
        
        icon = "✅" if status == 'success' else "❌"
        print(f"\n{icon} 任务: {task_id}")
        print(f"   状态: {status}")
        print(f"   创建时间: {item.get('created_at')}")
        
        if status == 'failed' and task_id:
            # 获取任务详情
            task_response = requests.get(f"{BASE_URL}/api/reports/tasks/{task_id}/status")
            if task_response.status_code == 200:
                task_data = task_response.json()
                for var in task_data.get('variables', []):
                    if var.get('status') == 'failed':
                        print(f"   ❌ 失败变量: {var['variable_name']}")
                        print(f"      错误: {var.get('error_message', 'Unknown')[:100]}")

def recommend_action(templates):
    """给出建议"""
    print("\n" + "=" * 60)
    print("建议操作")
    print("=" * 60)
    
    if not templates:
        print("✅ 没有发现包含 vision_ai 的旧模板")
        print("   如果你刚创建了模板，应该可以正常工作")
    else:
        print("⚠️  发现以下包含 vision_ai 的模板：")
        for tpl in templates:
            print(f"\n   - {tpl['name']} ({tpl['id']})")
            print(f"     创建于: {tpl['created_at']}")
        
        print("\n建议：")
        print("1. 如果这些模板创建于修复之前（2025-10-21 09:22之前）")
        print("   请删除并重新创建模板")
        print("\n2. 删除命令示例：")
        for tpl in templates[:1]:  # 只显示第一个作为示例
            print(f"   curl -X DELETE {BASE_URL}/api/templates/{tpl['id']}")

def main():
    print("Vision AI 问题诊断工具")
    print()
    
    # 1. 列出模板
    templates = list_templates()
    
    # 2. 检查最近任务
    check_recent_tasks()
    
    # 3. 给出建议
    recommend_action(templates)
    
    print("\n" + "=" * 60)
    print("✅ 诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()

