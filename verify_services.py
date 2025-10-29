#!/usr/bin/env python3
"""验证前后端服务是否正常运行"""
import requests
import time

print("=" * 60)
print("服务验证脚本")
print("=" * 60)

# 测试前端
print("\n1. 测试前端服务...")
try:
    response = requests.get("http://10.10.20.10:5173/", timeout=5)
    if response.status_code == 200:
        print("✅ 前端服务正常运行")
        print(f"   状态码: {response.status_code}")
        print(f"   内容长度: {len(response.text)} 字节")
        if '<div id="root">' in response.text:
            print("   ✅ HTML结构正常")
        else:
            print("   ⚠️  HTML结构可能有问题")
    else:
        print(f"❌ 前端响应异常: {response.status_code}")
except Exception as e:
    print(f"❌ 无法连接前端: {e}")

# 测试后端
print("\n2. 测试后端服务...")
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        print("✅ 后端服务正常运行")
        print(f"   响应: {response.json()}")
    else:
        print(f"❌ 后端响应异常: {response.status_code}")
except Exception as e:
    print(f"❌ 无法连接后端: {e}")

# 测试调试API
print("\n3. 测试调试API...")
try:
    response = requests.post(
        "http://localhost:8000/api/debug/render",
        json={
            "template_content": "# {{title}}",
            "metadata_yaml": """title:
  type: string
  source: user_input
  required: true
  description: 标题
  ui_config:
    input_type: text
""",
            "user_inputs": {"title": "测试标题"}
        },
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("✅ 调试API正常工作")
            print(f"   渲染结果: {data.get('rendered_markdown', '')[:50]}...")
        else:
            print(f"⚠️  调试API返回失败: {data.get('error')}")
    else:
        print(f"❌ 调试API响应异常: {response.status_code}")
        print(f"   错误: {response.text[:200]}")
except Exception as e:
    print(f"❌ 调试API请求失败: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
print("\n📝 下一步:")
print("1. 打开浏览器访问: http://10.10.20.10:5173/")
print("2. 访问调试页面: http://10.10.20.10:5173/debug")
print("3. 如果页面空白，请按 F12 打开浏览器控制台查看错误")
print("4. 清除浏览器缓存: Ctrl+Shift+Delete")


