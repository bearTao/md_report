#!/usr/bin/env python3
"""完整的Vision AI测试 - 测试URL和Base64两种格式"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_format(output_format, model_name):
    """测试特定的图片格式"""
    print(f"\n{'='*60}")
    print(f"测试 output_format: {output_format}, model: {model_name}")
    print('='*60)
    
    # 创建模板
    template_data = {
        "name": f"Vision AI测试 - {output_format}格式",
        "description": f"测试{output_format}格式的Vision AI功能",
        "template_content": """# 图片分析报告

## 图片
![图片]({{ test_image.data }})

## 分析结果
{{ analysis }}
""",
        "metadata": {
            "test_image": {
                "type": "image",
                "source": "image",
                "description": "测试图片",
                "image_config": {
                    "method": "GET",
                    "timeout": 30,
                    "endpoint": "https://picsum.photos/300/200",
                    "output_format": output_format
                }
            },
            "analysis": {
                "type": "string",
                "source": "vision_ai",
                "description": "图片分析",
                "dependencies": ["test_image"],
                "vision_ai_config": {
                    "model": model_name,
                    "max_tokens": 500,
                    "temperature": 0.3,
                    "image_source": "test_image",
                    "prompt_template": "请简短描述这张图片的内容（50字以内）"
                }
            }
        }
    }
    
    # 创建模板
    response = requests.post(f"{BASE_URL}/api/templates/", json=template_data)
    if response.status_code != 201:
        print(f"❌ 模板创建失败: {response.status_code}")
        return False
    
    template_id = response.json()['id']
    print(f"✅ 模板创建成功: {template_id}")
    
    # 生成报告
    response = requests.post(
        f"{BASE_URL}/api/reports/generate",
        json={"template_id": template_id, "inputs": {}}
    )
    
    if response.status_code != 202:
        print(f"❌ 报告生成失败: {response.status_code}")
        requests.delete(f"{BASE_URL}/api/templates/{template_id}")
        return False
    
    task_id = response.json()['task_id']
    print(f"✅ 任务创建成功: {task_id}")
    
    # 等待完成
    print("等待任务完成...", end='')
    for _ in range(30):
        time.sleep(2)
        response = requests.get(f"{BASE_URL}/api/reports/tasks/{task_id}/status")
        if response.status_code != 200:
            continue
        
        data = response.json()
        status = data['status']
        print('.', end='', flush=True)
        
        if status == 'success':
            print("\n✅ 任务成功完成！")
            
            # 显示变量执行结果
            for var in data.get('variables', []):
                status_icon = "✅" if var['status'] == 'success' else "❌"
                print(f"  {status_icon} {var['variable_name']}: {var['status']}")
            
            requests.delete(f"{BASE_URL}/api/templates/{template_id}")
            return True
        
        elif status == 'failed':
            print("\n❌ 任务失败")
            for var in data.get('variables', []):
                if var['status'] == 'failed':
                    print(f"  ❌ {var['variable_name']}: {var.get('error_message', 'Unknown')}")
            
            requests.delete(f"{BASE_URL}/api/templates/{template_id}")
            return False
    
    print("\n⏱️  超时")
    requests.delete(f"{BASE_URL}/api/templates/{template_id}")
    return False

def main():
    print("="*60)
    print("Vision AI 完整测试")
    print("="*60)
    
    # 测试配置
    tests = [
        {"format": "url", "model": "THUDM/GLM-4.1V-9B-Thinking"},
        {"format": "base64", "model": "THUDM/GLM-4.1V-9B-Thinking"},
    ]
    
    results = {}
    
    for test in tests:
        success = test_format(test["format"], test["model"])
        results[f"{test['format']}格式"] = success
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for name, success in results.items():
        icon = "✅" if success else "❌"
        print(f"{icon} {name}: {'通过' if success else '失败'}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 所有测试通过！Vision AI URL格式处理修复成功！")
    else:
        print("\n⚠️  部分测试失败，请检查配置")

if __name__ == "__main__":
    main()

