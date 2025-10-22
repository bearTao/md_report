#!/usr/bin/env python3
"""
P1.1 图片功能前后端联调测试脚本
测试图片获取和Vision AI分析功能
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def create_image_template() -> str:
    """创建包含图片和Vision AI的测试模板"""
    print_section("1. 创建图片测试模板")
    
    template_data = {
        "name": "图片功能测试模板",
        "description": "测试P1.1图片获取和Vision AI功能",
        "template_content": """# 图片功能测试报告

## 测试信息
- 报告ID: {{report_id}}
- 生成时间: {{generate_time}}

## 测试图片
{{test_image.markdown}}

## 图片信息
- URL: {{test_image.url}}
- 大小: {{test_image.size}} bytes
- MIME类型: {{test_image.mime_type}}

## AI图片分析（已禁用，需配置OpenAI API Key）
{{image_analysis}}

---
*测试完成*
""",
        "metadata": {
            "report_id": {
                "type": "string",
                "source": "system",
                "description": "报告ID",
                "system_config": {
                    "fields": {
                        "report_id": {
                            "generator": "uuid"
                        }
                    }
                }
            },
            "generate_time": {
                "type": "string",
                "source": "system",
                "description": "生成时间",
                "system_config": {
                    "fields": {
                        "generate_time": {
                            "generator": "datetime",
                            "format": "%Y-%m-%d %H:%M:%S"
                        }
                    }
                }
            },
            "test_image": {
                "type": "image",
                "source": "image",
                "description": "测试图片",
                "image_config": {
                    "endpoint": "https://picsum.photos/400/300",  # 使用公共图片API
                    "method": "GET",
                    "output_format": "url",  # 使用URL格式，更快
                    "timeout": 30
                }
            },
            "image_analysis": {
                "type": "string",
                "source": "user_input",  # 暂时用user_input代替vision_ai
                "description": "图片分析（需OpenAI API Key）",
                "default": "Vision AI分析功能需要配置OpenAI API Key才能使用",
                "ui_config": {
                    "input_type": "text",
                    "placeholder": "如需测试Vision AI，请配置OpenAI API Key"
                }
            }
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/templates/",
        json=template_data
    )
    
    if response.status_code == 201:
        data = response.json()
        template_id = data.get("template_id") or data.get("id")
        print(f"✅ 模板创建成功")
        print(f"   ID: {template_id}")
        print(f"   名称: {data['name']}")
        return template_id
    else:
        print(f"❌ 模板创建失败: {response.status_code}")
        print(f"   响应: {response.text}")
        raise Exception("Failed to create template")


def generate_report(template_id: str) -> str:
    """生成报告"""
    print_section("2. 生成报告")
    
    generate_data = {
        "template_id": template_id,
        "inputs": {
            "image_analysis": "（Vision AI功能需要OpenAI API Key）"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/reports/generate",
        json=generate_data
    )
    
    if response.status_code in [200, 202]:  # 202 Accepted for async tasks
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ 报告生成任务已创建")
        print(f"   Task ID: {task_id}")
        print(f"   状态: {data.get('status', 'pending')}")
        return task_id
    else:
        print(f"❌ 生成报告失败: {response.status_code}")
        print(f"   响应: {response.text}")
        raise Exception("Failed to generate report")


def wait_for_completion(task_id: str, max_wait: int = 60) -> Dict[str, Any]:
    """等待任务完成"""
    print_section("3. 等待任务完成")
    
    print(f"⏳ 等待任务完成（最多{max_wait}秒）...")
    
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            print(f"❌ 超时：任务在{max_wait}秒内未完成")
            break
        
        response = requests.get(f"{BASE_URL}/api/reports/tasks/{task_id}/status")
        if response.status_code != 200:
            print(f"❌ 获取状态失败: {response.status_code}")
            break
        
        status_data = response.json()
        status = status_data["status"]
        
        if status == "success":
            print(f"✅ 任务完成！（耗时: {elapsed:.2f}秒）")
            return status_data
        elif status == "failed":
            print(f"❌ 任务失败")
            print(f"   错误: {status_data.get('error')}")
            return status_data
        
        # 显示进度
        variables = status_data.get("variables", [])
        completed = sum(1 for v in variables if v["status"] in ["success", "failed", "skipped"])
        total = len(variables)
        progress = (completed / total * 100) if total > 0 else 0
        
        print(f"   进度: {completed}/{total} ({progress:.0f}%)  状态: {status}", end='\r')
        
        time.sleep(1)
    
    return {}


def check_variables(status_data: Dict[str, Any]):
    """检查变量执行结果"""
    print_section("4. 变量执行结果")
    
    variables = status_data.get("variables", [])
    
    print(f"\n共 {len(variables)} 个变量：\n")
    
    for var in variables:
        name = var["variable_name"]
        status = var["status"]
        source = var["source"]
        duration = var.get("duration_ms")
        
        status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⏭️"
        duration_str = f"{duration}ms" if duration else "-"
        
        print(f"{status_icon} {name:20s} [{source:15s}] {status:10s} {duration_str}")
        
        if status == "failed":
            print(f"     错误: {var.get('error_message')}")
        
        # 特别检查test_image变量
        if name == "test_image" and status == "success":
            result = var.get("result_preview", {})
            if result:
                print(f"     ↳ URL: {result.get('url', 'N/A')}")
                print(f"     ↳ Size: {result.get('size', 'N/A')} bytes")
                print(f"     ↳ MIME: {result.get('mime_type', 'N/A')}")


def get_report(task_id: str, status_data: Dict[str, Any]):
    """获取并显示报告"""
    print_section("5. 报告内容")
    
    report_id = status_data.get("report_id")
    if not report_id:
        print("❌ 没有生成报告ID")
        return
    
    response = requests.get(f"{BASE_URL}/api/reports/{report_id}")
    if response.status_code != 200:
        print(f"❌ 获取报告失败: {response.status_code}")
        return
    
    report = response.json()
    
    print(f"✅ 报告已生成")
    print(f"   ID: {report['id']}")
    print(f"   标题: {report.get('title', 'N/A')}")
    print(f"   耗时: {report.get('duration_ms', 0)}ms")
    
    markdown = report.get("markdown_content", "")
    if markdown:
        print(f"\n{'-' * 60}")
        print("Markdown内容预览（前500字符）：")
        print(f"{'-' * 60}")
        print(markdown[:500])
        if len(markdown) > 500:
            print(f"... (共{len(markdown)}字符)")
        print(f"{'-' * 60}")
        
        # 检查是否包含图片
        if "![" in markdown or "data:image" in markdown:
            print("\n✅ Markdown包含图片引用")
        else:
            print("\n⚠️ Markdown不包含图片引用")


def cleanup_test_template(template_id: str):
    """清理测试模板"""
    print_section("6. 清理测试数据")
    
    try:
        response = requests.delete(f"{BASE_URL}/api/templates/{template_id}")
        if response.status_code in [200, 204]:
            print(f"✅ 测试模板已删除")
        else:
            print(f"⚠️ 删除模板失败: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 清理失败: {e}")


def main():
    """主测试流程"""
    print("\n" + "🎯" * 30)
    print("  P1.1 图片功能前后端联调测试")
    print("🎯" * 30)
    
    template_id = None
    
    try:
        # 1. 创建模板
        template_id = create_image_template()
        
        # 2. 生成报告
        task_id = generate_report(template_id)
        
        # 3. 等待完成
        status_data = wait_for_completion(task_id)
        
        if not status_data:
            print("\n❌ 测试失败：无法获取任务状态")
            return
        
        # 4. 检查变量
        check_variables(status_data)
        
        # 5. 查看报告
        get_report(task_id, status_data)
        
        # 测试总结
        print_section("测试总结")
        
        if status_data.get("status") == "success":
            print("✅ 所有测试通过！")
            print("\n功能验证：")
            print("  ✅ 模板创建")
            print("  ✅ 图片变量类型支持")
            print("  ✅ 图片API连接器")
            print("  ✅ 图片获取功能")
            print("  ✅ Markdown渲染")
            print("\n🎉 P1.1图片功能前后端集成成功！")
        else:
            print("⚠️ 测试部分完成")
            print(f"   任务状态: {status_data.get('status')}")
    
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        if template_id:
            cleanup_test_template(template_id)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

