#!/usr/bin/env python3
"""测试用户的确切配置"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_user_config():
    """使用用户的确切配置进行测试"""
    
    template_data = {
        "name": "用户配置测试 - 产品质量检测",
        "description": "测试用户报告的bug",
        "template_content": """# 产品质量检测报告

## 产品信息
产品ID: {{ product_id }}

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
                "ui_config": {
                    "input_type": "text",
                    "placeholder": "请输入产品ID"
                },
                "description": "产品ID"
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
                    "output_format": "url"
                }
            },
            "quality_check": {
                "type": "string",
                "source": "vision_ai",
                "description": "质量检测报告",
                "dependencies": ["product_photo"],
                "vision_ai_config": {
                    "model": "THUDM/GLM-4.1V-9B-Thinking",
                    "max_tokens": 999999,
                    "temperature": 0.3,
                    "image_source": "product_photo",
                    "prompt_template": """请对这个产品进行质量检测：
1. 外观评价
2. 可见缺陷
3. 质量评分（1-10分）"""
                }
            }
        }
    }
    
    print("=" * 60)
    print("测试用户配置 - 产品质量检测")
    print("=" * 60)
    
    # 1. 创建模板
    print("\n1. 创建模板...")
    response = requests.post(f"{BASE_URL}/api/templates/", json=template_data)
    if response.status_code != 201:
        print(f"❌ 创建失败: {response.status_code}")
        print(response.text)
        return
    
    template_id = response.json()['id']
    print(f"✅ 模板ID: {template_id}")
    
    # 2. 生成报告
    print("\n2. 生成报告...")
    response = requests.post(
        f"{BASE_URL}/api/reports/generate",
        json={
            "template_id": template_id,
            "inputs": {"product_id": "TEST-001"}
        }
    )
    
    if response.status_code != 202:
        print(f"❌ 生成失败: {response.status_code}")
        print(response.text)
        requests.delete(f"{BASE_URL}/api/templates/{template_id}")
        return
    
    task_id = response.json()['task_id']
    print(f"✅ 任务ID: {task_id}")
    
    # 3. 等待完成并显示详细信息
    print("\n3. 等待任务完成...")
    for i in range(60):
        time.sleep(2)
        response = requests.get(f"{BASE_URL}/api/reports/tasks/{task_id}/status")
        
        if response.status_code != 200:
            continue
        
        data = response.json()
        status = data['status']
        
        print(f"  状态: {status}", end='\r')
        
        if status in ['success', 'failed']:
            print()
            print(f"\n{'='*60}")
            print(f"任务状态: {status}")
            print(f"{'='*60}")
            
            for var in data.get('variables', []):
                status_icon = "✅" if var['status'] == 'success' else "❌"
                print(f"\n{status_icon} {var['variable_name']}: {var['status']}")
                if var.get('error_message'):
                    print(f"   错误: {var['error_message']}")
                if var.get('duration_ms'):
                    print(f"   耗时: {var['duration_ms']}ms")
            
            break
    
    # 清理
    print(f"\n4. 清理...")
    requests.delete(f"{BASE_URL}/api/templates/{template_id}")
    print("✅ 完成")

if __name__ == "__main__":
    test_user_config()

