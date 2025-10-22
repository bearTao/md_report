#!/usr/bin/env python3
"""检查最近失败任务的详细错误信息"""
import requests
import json

BASE_URL = "http://localhost:8000"

def get_latest_task():
    """获取最近的任务"""
    response = requests.get(f"{BASE_URL}/api/reports/")
    if response.status_code == 200:
        data = response.json()
        if data['items']:
            return data['items'][0]['task_id']
    return None

def get_task_details(task_id):
    """获取任务详细信息"""
    response = requests.get(f"{BASE_URL}/api/reports/tasks/{task_id}/status")
    if response.status_code == 200:
        return response.json()
    return None

def main():
    print("=" * 60)
    print("检查最近任务错误信息")
    print("=" * 60)
    
    task_id = get_latest_task()
    if not task_id:
        print("❌ 没有找到任务")
        return
    
    print(f"\n任务ID: {task_id}")
    
    details = get_task_details(task_id)
    if details:
        print(f"状态: {details['status']}")
        print(f"\n变量执行详情:")
        for var in details.get('variables', []):
            print(f"  - {var['variable_name']}: {var['status']}")
            if var.get('error_message'):
                print(f"    错误: {var['error_message']}")
    else:
        print("❌ 无法获取任务详情")

if __name__ == "__main__":
    main()

