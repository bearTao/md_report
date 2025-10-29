"""简单测试嵌套模板生成"""
import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"

# 嵌套输入数据
nested_inputs = {
    "tpl_8d46934e172c": {  # 主模板
        "title": "主模板标题测试",
        "content": "主模板内容测试"
    },
    "tpl_e710aea7c613": {  # 子模板1
        "title1": "子模板1标题测试",
        "content1": "子模板1内容测试"
    }
}

print("="*60)
print("测试嵌套模板报告生成")
print("="*60)
print("\n嵌套输入数据:")
print(json.dumps(nested_inputs, indent=2, ensure_ascii=False))

# 1. 生成报告
print("\n1. 发起报告生成请求...")
response = requests.post(
    f"{BASE_URL}/api/reports/generate",
    json={
        "template_id": "tpl_8d46934e172c",
        "inputs": nested_inputs
    }
)

if response.status_code in [200, 202]:
    result = response.json()
    task_id = result["task_id"]
    print(f"✓ 任务创建成功: {task_id}")
else:
    print(f"✗ 请求失败: {response.status_code}")
    print(response.text)
    exit(1)

# 2. 等待执行完成
print(f"\n2. 等待任务执行...")
time.sleep(5)

# 3. 查看任务状态
print(f"\n3. 查看任务状态...")
response = requests.get(f"{BASE_URL}/api/reports/{task_id}/status")
if response.status_code == 200:
    status_data = response.json()
    print(f"任务状态: {status_data['task']['status']}")
    
    # 查看变量执行记录
    variables = status_data.get('generation_task_variables', [])
    print(f"\n变量执行记录 (共 {len(variables)} 个):")
    
    main_template_vars = []
    sub_template_vars = []
    
    for var in variables:
        template_id = var.get('template_id')
        template_path = var.get('template_path')
        var_name = var['variable_name']
        
        print(f"\n  变量: {var_name}")
        print(f"  所属模板: {template_id}")
        print(f"  模板路径: {template_path}")
        print(f"  状态: {var['status']}")
        
        if template_id == 'tpl_8d46934e172c':
            main_template_vars.append(var_name)
        elif template_id == 'tpl_e710aea7c613':
            sub_template_vars.append(var_name)
    
    print("\n" + "="*60)
    print("结果统计:")
    print("="*60)
    print(f"主模板变量 (tpl_8d46934e172c): {len(main_template_vars)} 个")
    if main_template_vars:
        print(f"  - {', '.join(main_template_vars)}")
    
    print(f"\n子模板变量 (tpl_e710aea7c613): {len(sub_template_vars)} 个")
    if sub_template_vars:
        print(f"  - {', '.join(sub_template_vars)}")
        print("\n✅ 成功！子模板变量已被正确记录！")
    else:
        print("\n❌ 失败！子模板变量未被记录")
    
else:
    print(f"✗ 获取状态失败: {response.status_code}")

# 4. 查看执行日志
print(f"\n4. 查看执行日志...")
response = requests.get(f"{BASE_URL}/api/reports/{task_id}/logs")
if response.status_code == 200:
    logs_data = response.json()
    logs = logs_data.get('logs', [])
    print(f"执行日志 (共 {len(logs)} 条):\n")
    
    for log in logs[:20]:  # 只显示前20条
        var_name = log.get('variable_name') or 'system'
        message = log['message']
        template_path = log.get('template_path') or '无'
        print(f"  [{log['level']}] {var_name}: {message[:60]}")
        if log.get('template_path'):
            print(f"     路径: {template_path}")

