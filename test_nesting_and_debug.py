#!/usr/bin/env python3
"""
Quick test script for template nesting and debug features
"""
import asyncio
import sys
sys.path.insert(0, '/data/tao/code/xuqiu/backend')

from app.database import SessionLocal
from app.models.db_models import Template
from app.services.renderer import template_renderer


async def test_nesting():
    """Test template nesting functionality"""
    print("=" * 60)
    print("测试模板嵌套功能")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Create test templates
        print("\n1. 创建测试模板...")
        
        # Child template
        child = Template(
            id="test_child_greeting",
            name="子模板：问候语",
            description="包含问候语的子模板",
            template_content="你好，{{user_name}}！欢迎使用模板嵌套功能。",
            metadata_json={
                "user_name": {
                    "type": "string",
                    "source": "user_input",
                    "required": True,
                    "description": "用户姓名",
                    "ui_config": {"input_type": "text"}
                }
            }
        )
        db.add(child)
        
        # Parent template
        parent = Template(
            id="test_parent_report",
            name="父模板：报告",
            description="包含子模板的主报告",
            template_content="""# {{report_title}}

## 欢迎信息
{% include "test_child_greeting" %}

## 报告内容
这是主报告的内容。
""",
            metadata_json={
                "report_title": {
                    "type": "string",
                    "source": "user_input",
                    "required": True,
                    "description": "报告标题",
                    "ui_config": {"input_type": "text"}
                }
            }
        )
        db.add(parent)
        db.commit()
        
        print("✅ 测试模板创建成功")
        
        # Test template nesting
        print("\n2. 测试模板嵌套...")
        user_inputs = {
            "report_title": "2024年度总结",
            "user_name": "张三"
        }
        
        resolved = await template_renderer._resolve_includes(
            parent.template_content,
            db,
            user_inputs
        )
        
        print("\n解析后的模板内容：")
        print("-" * 60)
        print(resolved)
        print("-" * 60)
        
        if "你好，张三" in resolved and "{% include" not in resolved:
            print("✅ 模板嵌套功能正常工作！")
        else:
            print("❌ 模板嵌套功能可能有问题")
        
        # Test circular include detection
        print("\n3. 测试循环嵌套检测...")
        
        circular_a = Template(
            id="test_circular_a",
            name="循环测试A",
            description="测试循环嵌套",
            template_content='A {% include "test_circular_b" %}',
            metadata_json={}
        )
        circular_b = Template(
            id="test_circular_b",
            name="循环测试B",
            description="测试循环嵌套",
            template_content='B {% include "test_circular_a" %}',
            metadata_json={}
        )
        db.add(circular_a)
        db.add(circular_b)
        db.commit()
        
        circular_resolved = await template_renderer._resolve_includes(
            circular_a.template_content,
            db,
            {}
        )
        
        if "ERROR: Circular include detected" in circular_resolved:
            print("✅ 循环嵌套检测正常工作！")
        else:
            print("❌ 循环嵌套检测可能有问题")
        
        # Cleanup
        print("\n4. 清理测试数据...")
        db.delete(child)
        db.delete(parent)
        db.delete(circular_a)
        db.delete(circular_b)
        db.commit()
        print("✅ 测试数据已清理")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def test_debug_api():
    """Test debug API (requires backend running)"""
    print("\n" + "=" * 60)
    print("测试调试API功能")
    print("=" * 60)
    
    try:
        import httpx
        
        print("\n检查后端服务是否运行...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    print("✅ 后端服务正在运行")
                else:
                    print("⚠️  后端服务状态异常")
                    return
            except httpx.ConnectError:
                print("⚠️  后端服务未运行，跳过API测试")
                print("   请先启动后端：cd backend && python -m uvicorn app.main:app")
                return
        
        print("\n发送调试请求...")
        request_data = {
            "template_content": "# {{title}}\n\n内容：{{content}}",
            "metadata_yaml": """title:
  type: string
  source: user_input
  required: true
  description: 标题
  ui_config:
    input_type: text

content:
  type: string
  source: user_input
  required: true
  description: 内容
  ui_config:
    input_type: textarea
""",
            "user_inputs": {
                "title": "测试报告",
                "content": "这是测试内容"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/debug/render",
                json=request_data,
                timeout=30.0
            )
        
        if response.status_code == 200:
            data = response.json()
            print("\n调试API响应：")
            print(f"  成功: {data['success']}")
            print(f"  变量数量: {len(data['variables'])}")
            if data['success']:
                print("\n渲染结果：")
                print("-" * 60)
                print(data['rendered_markdown'])
                print("-" * 60)
                print("✅ 调试API功能正常工作！")
            else:
                print(f"❌ 渲染失败: {data.get('error')}")
        else:
            print(f"❌ API请求失败: {response.status_code}")
            print(response.text)
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function"""
    print("\n🚀 开始测试模板嵌套和调试功能\n")
    
    # Test template nesting
    await test_nesting()
    
    # Test debug API
    await test_debug_api()
    
    print("\n" + "=" * 60)
    print("📊 测试完成总结")
    print("=" * 60)
    print("""
已完成测试：
✅ 模板嵌套基本功能
✅ 循环嵌套检测
✅ 调试API功能（如果后端运行）

后续步骤：
1. 启动后端: cd backend && python -m uvicorn app.main:app --reload
2. 启动前端: cd frontend && npm run dev
3. 访问调试页面: http://localhost:5173/debug
4. 在模板编辑页面测试"调试模板"按钮
5. 创建包含{% include %}标签的模板测试嵌套功能
""")


if __name__ == "__main__":
    asyncio.run(main())


