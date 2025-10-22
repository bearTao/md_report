#!/usr/bin/env python3
"""简化的图片功能测试脚本（带详细错误信息）"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def create_template():
    """创建测试模板"""
    template_data = {
        "id": f"test_img_tpl_{int(time.time())}",
        "name": "图片功能测试模板",
        "description": "测试图片获取功能",
        "template_content": "# 图片测试\n\n图片URL: {{ test_image.url }}\n\n![测试图片]({{ test_image.data }})",
        "metadata": {
            "test_image": {
                "type": "image",
                "source": "image",
                "required": True,
                "description": "测试图片",
                "image_config": {
                    "endpoint": "https://picsum.photos/200/300",
                    "method": "GET",
                    "output_format": "base64",
                    "timeout": 30
                }
            }
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/templates/", json=template_data)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code != 201:
        print(f"   错误: {response.text}")
        return None
    
    data = response.json()
    print(f"   模板ID: {data['id']}")
    return data['id']

def generate_report(template_id):
    """生成报告"""
    generate_data = {
        "template_id": template_id,
        "inputs": {}
    }
    
    response = requests.post(f"{BASE_URL}/api/reports/generate", json=generate_data)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code != 202:
        print(f"   错误: {response.text}")
        return None
    
    data = response.json()
    print(f"   任务ID: {data['task_id']}")
    return data['task_id']

def wait_for_completion(task_id, max_wait=30):
    """等待任务完成"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/api/reports/tasks/{task_id}/status")
        
        if response.status_code != 200:
            print(f"   ❌ 获取状态失败: {response.status_code}")
            return None
        
        data = response.json()
        status = data['status']
        var_count = len(data.get('variables', []))
        success_count = sum(1 for v in data.get('variables', []) if v['status'] == 'success')
        
        print(f"   {status} - {success_count}/{var_count}", end='  \r')
        
        if status in ['success', 'failed']:
            print()  # New line
            return data
        
        time.sleep(1)
    
    print("\n   ❌ 超时")
    return None

def get_report(report_id):
    """获取报告"""
    response = requests.get(f"{BASE_URL}/api/reports/{report_id}")
    
    if response.status_code != 200:
        print(f"   ❌ 获取失败: {response.status_code}")
        return None
    
    data = response.json()
    print(f"   标题: {data['title']}")
    print(f"   状态: {data['status']}")
    return data

def delete_template(template_id):
    """删除模板"""
    response = requests.delete(f"{BASE_URL}/api/templates/{template_id}")
    return response.status_code == 200

def main():
    print("=" * 60)
    print("简化图片功能测试（V2 - 详细错误）")
    print("=" * 60)
    
    template_id = None
    
    try:
        print("\n1. 创建模板...")
        template_id = create_template()
        if not template_id:
            return
        
        print("\n2. 生成报告...")
        task_id = generate_report(template_id)
        if not task_id:
            return
        
        print("\n3. 等待任务完成...")
        task_data = wait_for_completion(task_id)
        
        if task_data:
            if task_data['status'] == 'success':
                print("   ✅ 任务成功")
                
                print("\n4. 查看变量执行详情:")
                for var in task_data.get('variables', []):
                    print(f"   - {var['variable_name']}: {var['status']}")
                    if var.get('error_message'):
                        print(f"     错误: {var['error_message']}")
                
                if task_data.get('report_id'):
                    print("\n5. 获取报告...")
                    get_report(task_data['report_id'])
            else:
                print("   ❌ 任务失败")
                print("\n失败详情:")
                for var in task_data.get('variables', []):
                    if var['status'] == 'failed':
                        print(f"   - {var['variable_name']}: {var.get('error_message', 'Unknown error')}")
    
    finally:
        if template_id:
            print("\n6. 清理...")
            delete_template(template_id)
            print("   完成")

if __name__ == "__main__":
    main()

