#!/usr/bin/env python3
"""
测试模板嵌套的变量隔离功能
验证每个模板的user_input变量是独立的，同名变量不会相互影响
"""
import asyncio
import requests
import time
import sys
sys.path.insert(0, '/data/tao/code/xuqiu/backend')


def create_template(template_data):
    """创建模板"""
    response = requests.post(
        "http://localhost:8000/api/templates",
        json=template_data
    )
    if response.status_code in (200, 201):
        return response.json()
    else:
        raise Exception(f"Failed to create template: {response.status_code} - {response.text}")


def generate_report(template_id, inputs):
    """生成报告"""
    response = requests.post(
        "http://localhost:8000/api/reports/generate",
        json={
            "template_id": template_id,
            "inputs": inputs
        }
    )
    if response.status_code in (200, 202):
        return response.json()
    else:
        raise Exception(f"Failed to generate report: {response.status_code} - {response.text}")


def get_task_status(task_id):
    """获取任务状态"""
    response = requests.get(f"http://localhost:8000/api/reports/tasks/{task_id}/status")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get task status: {response.status_code}")


def get_report(report_id):
    """获取报告内容"""
    response = requests.get(f"http://localhost:8000/api/reports/{report_id}")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get report: {response.status_code}")


def delete_template(template_id):
    """删除模板"""
    try:
        requests.delete(f"http://localhost:8000/api/templates/{template_id}")
    except:
        pass


def main():
    print("=" * 70)
    print("测试嵌套模板的变量隔离功能")
    print("=" * 70)
    
    child_template_id = None
    parent_template_id = None
    
    try:
        # 1. 创建子模板（有 title 变量）
        print("\n1. 创建子模板...")
        child_template = create_template({
            "name": "测试子模板",
            "description": "用于测试变量隔离的子模板",
            "template_content": "## 子模板标题: {{title}}",
            "metadata": {
                "title": {
                    "type": "string",
                    "source": "user_input",
                    "required": True,
                    "description": "子模板标题",
                    "ui_config": {
                        "input_type": "text"
                    }
                }
            }
        })
        child_template_id = child_template["id"]
        print(f"✅ 子模板创建成功，ID: {child_template_id}")
        
        # 2. 创建主模板（也有 title 变量，并 include 子模板）
        print("\n2. 创建主模板（包含子模板）...")
        parent_template = create_template({
            "name": "测试主模板",
            "description": "用于测试变量隔离的主模板",
            "template_content": f'# 主模板标题: {{{{title}}}}\n\n{{% include "{child_template_id}" %}}',
            "metadata": {
                "title": {
                    "type": "string",
                    "source": "user_input",
                    "required": True,
                    "description": "主模板标题",
                    "ui_config": {
                        "input_type": "text"
                    }
                }
            }
        })
        parent_template_id = parent_template["id"]
        print(f"✅ 主模板创建成功，ID: {parent_template_id}")
        
        # 3. 生成报告，使用嵌套的inputs结构
        print("\n3. 生成报告（使用嵌套inputs）...")
        print("主模板 title = '主标题'")
        print("子模板 title = '子标题'")
        
        task = generate_report(
            parent_template_id,
            {
                parent_template_id: {"title": "主标题"},
                child_template_id: {"title": "子标题"}
            }
        )
        task_id = task["task_id"]
        print(f"✅ 任务已创建，task_id: {task_id}")
        
        # 4. 等待任务完成
        print("\n4. 等待任务完成...")
        max_wait = 30
        for i in range(max_wait):
            time.sleep(1)
            status = get_task_status(task_id)
            print(f"   [{i+1}/{max_wait}] 状态: {status['status']}")
            
            if status["status"] == "success":
                print("✅ 任务完成")
                report_id = status.get("report_id")
                break
            elif status["status"] == "failed":
                print(f"❌ 任务失败: {status.get('error')}")
                return
        else:
            print("❌ 任务超时")
            return
        
        # 5. 获取报告内容
        print("\n5. 获取报告内容...")
        report = get_report(report_id)
        markdown = report["markdown_content"]
        
        print("\n生成的报告内容：")
        print("-" * 70)
        print(markdown)
        print("-" * 70)
        
        # 6. 验证结果
        print("\n6. 验证变量隔离...")
        if "主模板标题: 主标题" in markdown:
            print("✅ 主模板的title变量正确（值为'主标题'）")
        else:
            print("❌ 主模板的title变量错误")
        
        if "子模板标题: 子标题" in markdown:
            print("✅ 子模板的title变量正确（值为'子标题'）")
        else:
            print("❌ 子模板的title变量错误")
        
        if "主模板标题: 主标题" in markdown and "子模板标题: 子标题" in markdown:
            print("\n" + "=" * 70)
            print("🎉 变量隔离功能测试通过！")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("❌ 变量隔离功能测试失败")
            print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        print("\n清理测试数据...")
        if child_template_id:
            delete_template(child_template_id)
            print(f"✅ 已删除子模板 {child_template_id}")
        if parent_template_id:
            delete_template(parent_template_id)
            print(f"✅ 已删除主模板 {parent_template_id}")


if __name__ == "__main__":
    main()


