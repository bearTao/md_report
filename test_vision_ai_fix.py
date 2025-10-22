#!/usr/bin/env python3
"""测试Vision AI修复 - 验证URL格式处理"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def create_template():
    """创建包含图片和视觉AI的测试模板"""
    template_data = {
        "name": "视觉AI测试模板 - URL格式",
        "description": "测试output_format: url时的Vision AI功能",
        "template_content": """# 产品质量检测报告

## 产品信息
- 产品ID: {{ product_id }}

## 产品照片
![产品照片]({{ product_photo.data }})

## 质量检测结果
{{ quality_check }}
""",
        "metadata": {
            "product_id": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "产品ID",
                "ui_config": {
                    "input_type": "text",
                    "placeholder": "请输入产品ID"
                }
            },
            "product_photo": {
                "type": "image",
                "source": "image",
                "description": "产品照片",
                "dependencies": ["product_id"],
                "image_config": {
                    "method": "GET",
                    "timeout": 30,
                    "endpoint": "https://picsum.photos/400/300",
                    "output_format": "url"  # 使用URL格式
                }
            },
            "quality_check": {
                "type": "string",
                "source": "vision_ai",
                "description": "质量检测报告",
                "dependencies": ["product_photo"],
                "vision_ai_config": {
                    "model": "gpt-4o-mini",
                    "max_tokens": 500,
                    "temperature": 0.3,
                    "image_source": "product_photo",
                    "prompt_template": "请对这个产品进行简短的质量检测，包括：1. 外观评价 2. 可见特征 3. 质量评分（1-10分）"
                }
            }
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/templates/", json=template_data)
    if response.status_code == 201:
        data = response.json()
        print(f"✅ 模板创建成功: {data['id']}")
        return data['id']
    else:
        print(f"❌ 模板创建失败: {response.status_code}")
        print(f"   错误: {response.text}")
        return None

def generate_report(template_id):
    """生成报告"""
    generate_data = {
        "template_id": template_id,
        "inputs": {
            "product_id": "TEST-VISION-001"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/reports/generate", json=generate_data)
    if response.status_code == 202:
        data = response.json()
        print(f"✅ 报告生成任务已创建: {data['task_id']}")
        return data['task_id']
    else:
        print(f"❌ 报告生成失败: {response.status_code}")
        print(f"   错误: {response.text}")
        return None

def wait_for_completion(task_id, max_wait=60):
    """等待任务完成"""
    print("\n等待任务完成...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/api/reports/tasks/{task_id}/status")
        
        if response.status_code != 200:
            print(f"❌ 获取状态失败: {response.status_code}")
            return None
        
        data = response.json()
        status = data['status']
        var_count = len(data.get('variables', []))
        success_count = sum(1 for v in data.get('variables', []) if v['status'] == 'success')
        
        print(f"  状态: {status} - {success_count}/{var_count} 变量完成", end='\r')
        
        if status == 'success':
            print("\n✅ 任务成功完成！")
            return data
        elif status == 'failed':
            print("\n❌ 任务失败")
            print("\n失败详情:")
            for var in data.get('variables', []):
                if var['status'] == 'failed':
                    print(f"  - {var['variable_name']}: {var.get('error_message', 'Unknown error')}")
            return data
        
        time.sleep(2)
    
    print("\n❌ 等待超时")
    return None

def get_report(report_id):
    """获取报告内容"""
    response = requests.get(f"{BASE_URL}/api/reports/{report_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📄 报告内容:")
        print("=" * 60)
        print(data['markdown_content'][:500])
        if len(data['markdown_content']) > 500:
            print("...")
        print("=" * 60)
        return data
    else:
        print(f"❌ 获取报告失败: {response.status_code}")
        return None

def delete_template(template_id):
    """删除测试模板"""
    response = requests.delete(f"{BASE_URL}/api/templates/{template_id}")
    if response.status_code == 204:
        print(f"✅ 模板已删除")
        return True
    else:
        print(f"⚠️  删除模板失败: {response.status_code}")
        return False

def main():
    print("=" * 60)
    print("Vision AI 修复测试 - URL格式处理")
    print("=" * 60)
    
    template_id = None
    
    try:
        print("\n1️⃣  创建测试模板...")
        template_id = create_template()
        if not template_id:
            return
        
        print("\n2️⃣  生成报告...")
        task_id = generate_report(template_id)
        if not task_id:
            return
        
        print("\n3️⃣  等待任务完成...")
        task_data = wait_for_completion(task_id)
        
        if task_data and task_data['status'] == 'success':
            print("\n4️⃣  查看变量执行详情:")
            for var in task_data.get('variables', []):
                status_icon = "✅" if var['status'] == 'success' else "❌"
                print(f"  {status_icon} {var['variable_name']}: {var['status']}")
                if var.get('error_message'):
                    print(f"     错误: {var['error_message']}")
            
            if task_data.get('report_id'):
                print("\n5️⃣  获取报告...")
                get_report(task_data['report_id'])
            
            print("\n🎉 测试通过！Vision AI 可以正确处理 URL 格式的图片！")
        else:
            print("\n❌ 测试失败")
    
    finally:
        if template_id:
            print("\n6️⃣  清理测试数据...")
            delete_template(template_id)

if __name__ == "__main__":
    main()

