"""
示例：完整的报告生成流程演示
运行: python example_usage.py
"""
import asyncio
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import (
    VariableMetadata, VariableSource, SystemConfig, UiConfig, VariableStatus,
    SqlConfig, SqlResultMode, ApiConfig, AiConfig
)
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


async def example_simple_report():
    """示例1: 简单的项目报告生成"""
    print("=" * 60)
    print("示例1: 简单项目报告生成")
    print("=" * 60)
    
    # 定义变量元数据
    metadata = {
        "report_title": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="报告标题",
            required=True,
            ui_config=UiConfig(
                input_type="text",
                placeholder="请输入报告标题"
            )
        ),
        "project_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="项目名称",
            required=True,
            ui_config=UiConfig(input_type="text")
        ),
        "report_date": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="报告日期",
            required=True,
            system_config=SystemConfig(
                fields={
                    "date": {
                        "generator": "datetime",
                        "format": "%Y年%m月%d日"
                    }
                }
            )
        ),
        "generation_info": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="生成信息",
            required=True,
            system_config=SystemConfig(
                fields={
                    "timestamp": {
                        "generator": "datetime",
                        "format": "%Y-%m-%d %H:%M:%S"
                    },
                    "report_id": {
                        "generator": "uuid"
                    },
                    "version": {
                        "value": "1.0.0"
                    }
                }
            )
        )
    }
    
    # 用户输入
    user_inputs = {
        "report_title": "2025年Q3季度总结报告",
        "project_name": "智能报告生成系统"
    }
    
    # 创建执行上下文
    context = ExecutionContext(
        task_id="demo_task_001",
        template_id="demo_template_001",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # 执行所有变量
    scheduler = ExecutionScheduler()
    
    print("\n执行变量...")
    results = await scheduler.execute_all(context)
    
    # 打印执行结果
    print("\n变量执行结果:")
    for var_name, result in results.items():
        status_icon = "✅" if result.status == VariableStatus.SUCCESS else "❌"
        print(f"{status_icon} {var_name}: {result.status.value} ({result.duration_ms}ms)")
    
    # 定义模板
    template_content = """# {{report_title}}

## 项目信息

- **项目名称**: {{project_name}}
- **报告日期**: {{report_date}}
- **报告版本**: {{generation_info.version}}

## 生成信息

- **生成时间**: {{generation_info.timestamp}}
- **报告ID**: {{generation_info.report_id}}

## 项目概况

本报告总结了「{{project_name}}」项目在本季度的主要工作进展、取得的成果以及下一步的工作计划。

## 工作亮点

1. 完成核心功能开发
2. 通过系统测试
3. 优化用户体验

---
*本报告由系统自动生成于 {{generation_info.timestamp}}*
"""
    
    # 渲染模板
    print("\n渲染报告...")
    markdown = template_renderer.render(template_content, context.get_all_variables())
    
    # 输出结果
    print("\n" + "=" * 60)
    print("生成的Markdown报告:")
    print("=" * 60)
    print(markdown)
    print("=" * 60)


async def example_with_dependencies():
    """示例2: 带依赖关系的变量执行"""
    print("\n\n" + "=" * 60)
    print("示例2: 带依赖关系的变量执行")
    print("=" * 60)
    
    metadata = {
        "user_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="用户名",
            required=True
        ),
        "department": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="部门",
            required=True
        ),
        "greeting_message": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="问候语",
            required=True,
            dependencies=["user_name", "department"],  # 依赖前两个变量
            system_config=SystemConfig(
                fields={
                    "message": {
                        "value": "已生成 {{user_name}} 的问候语，部门为 {{department}}"
                    }
                }
            )
        )
    }
    
    user_inputs = {
        "user_name": "张三",
        "department": "技术部"
    }
    
    context = ExecutionContext(
        task_id="demo_task_002",
        template_id="demo_template_002",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    scheduler = ExecutionScheduler()
    
    # 构建DAG并显示执行计划
    dag = scheduler.build_dag(metadata)
    batches = scheduler.get_execution_batches(dag)
    
    print("\n执行计划（按批次）:")
    for i, batch in enumerate(batches, 1):
        print(f"批次 {i}: {', '.join(batch)}")
    
    print("\n开始执行...")
    results = await scheduler.execute_all(context)
    
    print("\n执行结果:")
    for var_name, result in results.items():
        status_icon = "✅" if result.status == VariableStatus.SUCCESS else "❌"
        value_preview = str(result.value)[:50]
        print(f"{status_icon} {var_name}: {value_preview}")
    
    # 使用变量插值功能
    template = """
员工信息卡片
============

姓名: {{user_name}}
部门: {{department}}
状态: {{greeting_message}}

欢迎 {{user_name}} 加入 {{department}}！
"""
    
    markdown = template_renderer.render(template, context.get_all_variables())
    print("\n生成的内容:")
    print(markdown)


async def example_sql_result_modes():
    """示例3: SQL变量所有ResultMode类型演示"""
    print("\n\n" + "=" * 60)
    print("示例3: SQL变量ResultMode完整演示")
    print("=" * 60)
    print("\n本示例展示所有5种SQL result_mode的配置方式")
    print("注意：这是配置示例，实际运行需要配置数据库连接\n")
    
    # 定义包含所有SQL result_mode类型的变量元数据
    metadata = {
        # 1. FIRST_ROW模式 - 返回第一行作为对象
        "user_profile": VariableMetadata(
            type="object",
            source=VariableSource.SQL,
            description="用户档案信息（单个对象）",
            required=False,
            default={},
            dependencies=["user_id"],
            sql_config=SqlConfig(
                connection="user_db",
                query="SELECT id, name, email, department, role, hire_date FROM users WHERE id = {{user_id}}",
                parameters=["user_id"],
                timeout=10,
                result_mode=SqlResultMode.FIRST_ROW  # 返回 {id: 1, name: "Alice", ...}
            ),
            schema={
                "type": "object",
                "properties": {
                    "id": {"type": "number"},
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "department": {"type": "string"},
                    "role": {"type": "string"},
                    "hire_date": {"type": "string"}
                }
            }
        ),
        
        # 2. ALL_ROWS模式 - 返回所有行作为数组
        "team_members": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="团队成员列表（数组）",
            required=False,
            default=[],
            dependencies=["department_id"],
            sql_config=SqlConfig(
                connection="user_db",
                query="""
                SELECT id, name, email, role, performance_score 
                FROM users 
                WHERE department_id = {{department_id}} AND status = 'active'
                ORDER BY performance_score DESC
                """,
                parameters=["department_id"],
                timeout=10,
                result_mode=SqlResultMode.ALL_ROWS  # 返回 [{row1}, {row2}, ...]
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "number"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "role": {"type": "string"},
                        "performance_score": {"type": "number"}
                    }
                }
            }
        ),
        
        # 3. FIRST_VALUE模式 - 返回第一行第一列的标量值
        "total_sales": VariableMetadata(
            type="number",
            source=VariableSource.SQL,
            description="总销售额（标量数值）",
            required=False,
            default=0,
            dependencies=["start_date", "end_date"],
            sql_config=SqlConfig(
                connection="analytics_db",
                query="""
                SELECT SUM(amount) as total
                FROM sales 
                WHERE date BETWEEN {{start_date}} AND {{end_date}}
                  AND status = 'completed'
                """,
                parameters=["start_date", "end_date"],
                timeout=15,
                result_mode=SqlResultMode.FIRST_VALUE  # 返回标量: 12345.67
            )
        ),
        
        "active_user_count": VariableMetadata(
            type="number",
            source=VariableSource.SQL,
            description="活跃用户数量（标量整数）",
            required=False,
            default=0,
            sql_config=SqlConfig(
                connection="user_db",
                query="""
                SELECT COUNT(*) as count
                FROM users 
                WHERE status = 'active' 
                  AND last_login > DATE_SUB(NOW(), INTERVAL 30 DAY)
                """,
                timeout=10,
                result_mode=SqlResultMode.FIRST_VALUE  # 返回标量: 156
            )
        ),
        
        # 4. FIRST_COLUMN模式 - 返回第一列的所有值
        "product_ids": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="产品ID列表（单列数组）",
            required=False,
            default=[],
            dependencies=["category_id"],
            sql_config=SqlConfig(
                connection="product_db",
                query="""
                SELECT id 
                FROM products 
                WHERE category_id = {{category_id}} 
                  AND stock > 0
                ORDER BY created_at DESC
                """,
                parameters=["category_id"],
                timeout=10,
                result_mode=SqlResultMode.FIRST_COLUMN  # 返回 [101, 102, 103, ...]
            ),
            schema={
                "type": "array",
                "items": {"type": "number"}
            }
        ),
        
        "top_customer_names": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="顶级客户名称列表（单列数组）",
            required=False,
            default=[],
            sql_config=SqlConfig(
                connection="crm_db",
                query="""
                SELECT customer_name
                FROM customers
                WHERE total_purchase > 10000
                ORDER BY total_purchase DESC
                LIMIT 10
                """,
                timeout=10,
                result_mode=SqlResultMode.FIRST_COLUMN  # 返回 ["Customer A", "Customer B", ...]
            ),
            schema={
                "type": "array",
                "items": {"type": "string"}
            }
        ),
        
        # 5. AUTO模式 - 根据type自动判断
        "company_info": VariableMetadata(
            type="object",
            source=VariableSource.SQL,
            description="公司信息（自动模式-对象）",
            required=False,
            default={},
            sql_config=SqlConfig(
                connection="master_db",
                query="""
                SELECT 
                    name, 
                    industry, 
                    employee_count, 
                    annual_revenue,
                    founded_year
                FROM companies 
                WHERE id = 1
                """,
                timeout=10,
                result_mode=SqlResultMode.AUTO  # 自动：单行object返回字典
            ),
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "industry": {"type": "string"},
                    "employee_count": {"type": "number"},
                    "annual_revenue": {"type": "number"},
                    "founded_year": {"type": "number"}
                }
            }
        ),
        
        "recent_orders": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="近期订单（自动模式-数组）",
            required=False,
            default=[],
            sql_config=SqlConfig(
                connection="order_db",
                query="""
                SELECT 
                    order_id,
                    customer_name,
                    total_amount,
                    order_date,
                    status
                FROM orders 
                WHERE order_date > DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY order_date DESC
                LIMIT 20
                """,
                timeout=10,
                result_mode=SqlResultMode.AUTO  # 自动：array类型返回所有行
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "customer_name": {"type": "string"},
                        "total_amount": {"type": "number"},
                        "order_date": {"type": "string"},
                        "status": {"type": "string"}
                    }
                }
            }
        ),
        
        # 用户输入变量（作为SQL查询参数）
        "user_id": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="用户ID",
            required=True,
            ui_config=UiConfig(input_type="number")
        ),
        
        "department_id": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="部门ID",
            required=True,
            ui_config=UiConfig(input_type="number")
        ),
        
        "category_id": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="类别ID",
            required=True,
            ui_config=UiConfig(input_type="number")
        ),
        
        "start_date": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="开始日期",
            required=True,
            ui_config=UiConfig(input_type="date")
        ),
        
        "end_date": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="结束日期",
            required=True,
            ui_config=UiConfig(input_type="date")
        ),
        
        # 系统变量
        "report_date": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="报告日期",
            required=True,
            system_config=SystemConfig(
                fields={
                    "date": {
                        "generator": "datetime",
                        "format": "%Y-%m-%d"
                    }
                }
            )
        )
    }
    
    # 打印配置信息
    print("📋 变量配置概览:\n")
    
    result_mode_vars = {
        "FIRST_ROW (返回第一行对象)": ["user_profile"],
        "ALL_ROWS (返回所有行数组)": ["team_members"],
        "FIRST_VALUE (返回标量值)": ["total_sales", "active_user_count"],
        "FIRST_COLUMN (返回单列数组)": ["product_ids", "top_customer_names"],
        "AUTO (自动判断)": ["company_info", "recent_orders"]
    }
    
    for mode, vars in result_mode_vars.items():
        print(f"\n{mode}:")
        for var_name in vars:
            var_meta = metadata[var_name]
            print(f"  • {var_name}: {var_meta.description}")
            if var_meta.sql_config:
                # 简化显示SQL查询
                query_preview = var_meta.sql_config.query.strip().split('\n')[0][:60]
                print(f"    SQL: {query_preview}...")
    
    # 定义复杂的Markdown模板
    template_content = """# 企业数据分析报告

生成日期: {{report_date}}

---

## 一、用户分析

### 1.1 用户档案 (FIRST_ROW模式)

**查询用户**: {{user_profile.name}} (ID: {{user_profile.id}})

- **邮箱**: {{user_profile.email}}
- **部门**: {{user_profile.department}}
- **职位**: {{user_profile.role}}
- **入职日期**: {{user_profile.hire_date}}

> 💡 **说明**: `result_mode: FIRST_ROW` 返回单个用户对象，适合查询单条记录的详细信息。

---

### 1.2 团队成员列表 (ALL_ROWS模式)

**部门成员** (共 {{team_members|length}} 人):

{% for member in team_members %}
{{loop.index}}. **{{member.name}}** - {{member.role}}
   - 邮箱: {{member.email}}
   - 绩效分数: {{member.performance_score}}/100
{% endfor %}

> 💡 **说明**: `result_mode: ALL_ROWS` 返回完整的成员列表，适合需要遍历所有记录的场景。

---

## 二、业务指标 (FIRST_VALUE模式)

### 2.1 销售数据

- **统计期间**: {{start_date}} 至 {{end_date}}
- **总销售额**: ¥{{total_sales|round(2)}}
- **活跃用户数**: {{active_user_count}} 人

> 💡 **说明**: `result_mode: FIRST_VALUE` 返回聚合函数的标量结果，如 SUM、COUNT、AVG 等。

---

## 三、产品信息 (FIRST_COLUMN模式)

### 3.1 在售产品ID列表

类别 {{category_id}} 的在售产品ID:
{% for pid in product_ids %}
- Product #{{pid}}
{% endfor %}

**总计**: {{product_ids|length}} 个产品

### 3.2 顶级客户名单

Top 10 客户:
{% for name in top_customer_names %}
{{loop.index}}. {{name}}
{% endfor %}

> 💡 **说明**: `result_mode: FIRST_COLUMN` 只返回第一列的值列表，适合需要ID列表、名称列表等场景。

---

## 四、综合信息 (AUTO模式)

### 4.1 公司概况

**{{company_info.name}}**

- 所属行业: {{company_info.industry}}
- 员工规模: {{company_info.employee_count}} 人
- 年度营收: ¥{{company_info.annual_revenue}} 元
- 成立年份: {{company_info.founded_year}}

> 💡 **说明**: `result_mode: AUTO` + `type: object` 智能判断，单行返回对象。

### 4.2 近期订单

最近7天订单 (共 {{recent_orders|length}} 笔):

| 订单号 | 客户名称 | 金额 | 日期 | 状态 |
|--------|----------|------|------|------|
{% for order in recent_orders[:5] %}
| {{order.order_id}} | {{order.customer_name}} | ¥{{order.total_amount}} | {{order.order_date}} | {{order.status}} |
{% endfor %}

> 💡 **说明**: `result_mode: AUTO` + `type: array` 智能判断，返回所有行的数组。

---

## 五、ResultMode选择指南

| 场景 | 推荐模式 | 示例 |
|------|----------|------|
| 查询单条完整记录 | `FIRST_ROW` | 用户详情、商品详情 |
| 查询多条完整记录 | `ALL_ROWS` | 订单列表、用户列表 |
| 统计聚合结果 | `FIRST_VALUE` | SUM、COUNT、AVG、MAX |
| 仅需ID或名称列表 | `FIRST_COLUMN` | 产品ID、用户名 |
| 让系统智能判断 | `AUTO` | 大多数常规场景 |

---

*本报告由智能报告生成系统自动生成，使用了全部5种SQL ResultMode*
"""
    
    print("\n\n" + "=" * 60)
    print("📄 生成的Markdown模板预览:")
    print("=" * 60)
    print("\n模板长度:", len(template_content), "字符")
    print("包含变量引用:")
    
    import re
    variables_in_template = set(re.findall(r'\{\{(\w+(?:\.\w+)?)', template_content))
    for var in sorted(variables_in_template):
        print(f"  • {var}")
    
    print("\n\n" + "=" * 60)
    print("✅ SQL ResultMode完整示例配置展示完成")
    print("=" * 60)
    print("\n💡 提示:")
    print("1. 实际使用时需要先配置数据库连接: db_connector.register_connection()")
    print("2. 根据实际数据表结构调整SQL查询语句")
    print("3. AUTO模式是默认值，适合大多数场景")
    print("4. 选择明确的模式可以提高代码可读性和可维护性")


async def example_complex_real_report():
    """示例4: 复杂的真实项目分析报告"""
    print("\n\n" + "=" * 80)
    print("示例4: 复杂的真实项目分析报告生成")
    print("=" * 80)
    
    # 用户输入数据（提前定义以便预计算）
    user_inputs = {
        "project_name": "企业级智能客服平台",
        "project_manager": "张经理",
        "team_size": 12,
        "report_period": "Q3",
        "budget": 500,
        "actual_cost": 435
    }
    
    # 预计算一些值
    budget = user_inputs["budget"]
    actual_cost = user_inputs["actual_cost"]
    team_size = user_inputs["team_size"]
    remaining = budget - actual_cost
    usage_rate = round((actual_cost / budget * 100), 2)
    status = "正常" if actual_cost <= budget else ("警告" if actual_cost <= budget * 1.1 else "超支")
    avg_cost_per_person = round(actual_cost / team_size, 2)
    team_level = "小型团队" if team_size < 5 else ("中型团队" if team_size < 15 else "大型团队")
    
    # 定义复杂的变量元数据
    metadata = {
        # === 基础信息（用户输入）===
        "project_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="项目名称",
            required=True,
            ui_config=UiConfig(
                input_type="text",
                placeholder="例如：智能客服系统"
            )
        ),
        
        "project_manager": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="项目经理",
            required=True,
            ui_config=UiConfig(input_type="text")
        ),
        
        "team_size": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="团队规模",
            required=True,
            ui_config=UiConfig(input_type="number")
        ),
        
        "report_period": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="报告周期",
            required=True,
            ui_config=UiConfig(
                input_type="select",
                options=["Q1", "Q2", "Q3", "Q4", "H1", "H2", "全年"]
            )
        ),
        
        "budget": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="项目预算（万元）",
            required=True,
            ui_config=UiConfig(input_type="number")
        ),
        
        "actual_cost": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="实际支出（万元）",
            required=True,
            ui_config=UiConfig(input_type="number")
        ),
        
        # === 系统生成变量 ===
        "report_metadata": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="报告元数据",
            required=True,
            system_config=SystemConfig(
                fields={
                    "report_id": {
                        "generator": "uuid"
                    },
                    "generated_at": {
                        "generator": "datetime",
                        "format": "%Y-%m-%d %H:%M:%S"
                    },
                    "report_date": {
                        "generator": "datetime",
                        "format": "%Y年%m月%d日"
                    },
                    "version": {
                        "value": "2.0.0"
                    },
                    "author": {
                        "value": "智能报告生成系统"
                    }
                }
            )
        ),
        
        # === 计算型变量（依赖其他变量）===
        "budget_status": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="预算状态分析",
            required=True,
            dependencies=["budget", "actual_cost"],
            system_config=SystemConfig(
                fields={
                    "budget": {
                        "value": "{{budget}}"
                    },
                    "actual_cost": {
                        "value": "{{actual_cost}}"
                    },
                    "remaining": {
                        "value": remaining
                    },
                    "usage_rate": {
                        "value": usage_rate
                    },
                    "status": {
                        "value": status
                    }
                }
            )
        ),
        
        "team_efficiency": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="团队效率指标",
            required=True,
            dependencies=["team_size", "actual_cost"],
            system_config=SystemConfig(
                fields={
                    "avg_cost_per_person": {
                        "value": avg_cost_per_person
                    },
                    "team_level": {
                        "value": team_level
                    }
                }
            )
        ),
        
        # === 模拟项目数据（数组类型）===
        "milestones": VariableMetadata(
            type="array",
            source=VariableSource.SYSTEM,
            description="项目里程碑",
            required=True,
            dependencies=["project_name"],
            system_config=SystemConfig(
                fields={
                    "items": {
                        "value": [
                            {
                                "name": "需求分析完成",
                                "planned_date": "2025-01-15",
                                "actual_date": "2025-01-18",
                                "status": "已完成",
                                "delay_days": 3,
                                "completion": 100
                            },
                            {
                                "name": "架构设计评审",
                                "planned_date": "2025-02-01",
                                "actual_date": "2025-02-01",
                                "status": "已完成",
                                "delay_days": 0,
                                "completion": 100
                            },
                            {
                                "name": "核心功能开发",
                                "planned_date": "2025-04-30",
                                "actual_date": "2025-05-10",
                                "status": "已完成",
                                "delay_days": 10,
                                "completion": 100
                            },
                            {
                                "name": "系统测试",
                                "planned_date": "2025-06-15",
                                "actual_date": "2025-06-20",
                                "status": "已完成",
                                "delay_days": 5,
                                "completion": 100
                            },
                            {
                                "name": "用户验收测试",
                                "planned_date": "2025-07-30",
                                "actual_date": None,
                                "status": "进行中",
                                "delay_days": 0,
                                "completion": 75
                            },
                            {
                                "name": "正式上线",
                                "planned_date": "2025-08-15",
                                "actual_date": None,
                                "status": "未开始",
                                "delay_days": 0,
                                "completion": 0
                            }
                        ]
                    }
                }
            )
        ),
        
        "team_members": VariableMetadata(
            type="array",
            source=VariableSource.SYSTEM,
            description="团队成员信息",
            required=True,
            dependencies=["project_manager", "team_size"],
            system_config=SystemConfig(
                fields={
                    "items": {
                        "value": [
                            {
                                "name": "{{project_manager}}",
                                "role": "项目经理",
                                "tasks_completed": 28,
                                "performance": 95
                            },
                            {
                                "name": "李工",
                                "role": "技术负责人",
                                "tasks_completed": 45,
                                "performance": 92
                            },
                            {
                                "name": "王工",
                                "role": "前端开发",
                                "tasks_completed": 38,
                                "performance": 88
                            },
                            {
                                "name": "赵工",
                                "role": "后端开发",
                                "tasks_completed": 42,
                                "performance": 90
                            },
                            {
                                "name": "刘工",
                                "role": "测试工程师",
                                "tasks_completed": 35,
                                "performance": 87
                            }
                        ]
                    }
                }
            )
        ),
        
        "risk_assessment": VariableMetadata(
            type="array",
            source=VariableSource.SYSTEM,
            description="风险评估",
            required=True,
            dependencies=["budget_status"],
            system_config=SystemConfig(
                fields={
                    "items": {
                        "value": [
                            {
                                "category": "进度风险",
                                "description": "部分里程碑存在延期",
                                "level": "中",
                                "mitigation": "加强进度跟踪，必要时增加资源投入"
                            },
                            {
                                "category": "预算风险",
                                "description": f"预算使用率: {usage_rate}%",
                                "level": "高" if usage_rate > 100 else ("中" if usage_rate > 90 else "低"),
                                "mitigation": "严格控制成本，优化资源配置"
                            },
                            {
                                "category": "技术风险",
                                "description": "新技术栈学习曲线较陡",
                                "level": "中",
                                "mitigation": "组织技术培训，安排技术预研"
                            },
                            {
                                "category": "人员风险",
                                "description": "核心成员工作饱和度高",
                                "level": "低",
                                "mitigation": "合理分配任务，避免过度加班"
                            }
                        ]
                    }
                }
            )
        ),
        
        "achievements": VariableMetadata(
            type="array",
            source=VariableSource.SYSTEM,
            description="主要成果",
            required=True,
            dependencies=["project_name"],
            system_config=SystemConfig(
                fields={
                    "items": {
                        "value": [
                            {
                                "title": "核心架构设计完成",
                                "description": "完成了系统的整体架构设计，采用微服务架构，支持高并发场景",
                                "impact": "为系统的可扩展性和可维护性奠定了基础",
                                "date": "2025-02-01"
                            },
                            {
                                "title": "用户认证模块上线",
                                "description": "实现了完整的用户认证授权系统，支持多种登录方式",
                                "impact": "提升了系统安全性，用户体验良好",
                                "date": "2025-03-15"
                            },
                            {
                                "title": "数据分析功能发布",
                                "description": "开发了实时数据分析和可视化功能，提供丰富的报表",
                                "impact": "帮助运营团队更好地了解业务数据，支持决策",
                                "date": "2025-05-20"
                            },
                            {
                                "title": "性能优化达标",
                                "description": "通过多轮优化，系统响应时间控制在100ms以内",
                                "impact": "显著提升用户体验，系统稳定性提高",
                                "date": "2025-06-10"
                            }
                        ]
                    }
                }
            )
        ),
        
        "kpi_metrics": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="KPI指标",
            required=True,
            dependencies=["milestones"],
            system_config=SystemConfig(
                fields={
                    "overall_progress": {
                        "value": 68
                    },
                    "on_time_rate": {
                        "value": 66.7
                    },
                    "quality_score": {
                        "value": 91.5
                    },
                    "customer_satisfaction": {
                        "value": 4.5
                    },
                    "code_coverage": {
                        "value": 85
                    },
                    "bug_density": {
                        "value": 0.8
                    }
                }
            )
        )
    }
    
    # 创建执行上下文
    context = ExecutionContext(
        task_id="complex_report_001",
        template_id="complex_template_001",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # 执行所有变量
    scheduler = ExecutionScheduler()
    
    # 显示执行计划
    dag = scheduler.build_dag(metadata)
    batches = scheduler.get_execution_batches(dag)
    
    print("\n📋 执行计划（按批次）:")
    for i, batch in enumerate(batches, 1):
        print(f"  批次 {i}: {', '.join(batch)}")
    
    print("\n⚙️  开始执行变量...")
    results = await scheduler.execute_all(context)
    
    # 打印执行结果
    print("\n✅ 变量执行结果:")
    for var_name, result in results.items():
        status_icon = "✅" if result.status == VariableStatus.SUCCESS else "❌"
        print(f"  {status_icon} {var_name}: {result.status.value} ({result.duration_ms}ms)")
    
    # 定义复杂的Markdown模板
    template_content = """# {{project_name}} - {{report_period}}季度分析报告

**报告ID**: `{{report_metadata.report_id}}`  
**生成日期**: {{report_metadata.report_date}}  
**报告版本**: {{report_metadata.version}}  
**项目经理**: {{project_manager}}

---

## 📊 执行摘要

本报告对「**{{project_name}}**」项目在{{report_period}}季度的执行情况进行全面分析。项目由{{project_manager}}领导，团队规模{{team_size}}人（{{team_efficiency.team_level}}）。

### 核心指标概览

| 指标 | 数值 | 状态 |
|------|------|------|
| 整体进度 | {{kpi_metrics.overall_progress}}% | {% if kpi_metrics.overall_progress >= 80 %}🟢 优秀{% elif kpi_metrics.overall_progress >= 60 %}🟡 良好{% else %}🔴 需改进{% endif %} |
| 按时完成率 | {{kpi_metrics.on_time_rate}}% | {% if kpi_metrics.on_time_rate >= 80 %}🟢 优秀{% elif kpi_metrics.on_time_rate >= 60 %}🟡 良好{% else %}🔴 需改进{% endif %} |
| 质量评分 | {{kpi_metrics.quality_score}}/100 | {% if kpi_metrics.quality_score >= 90 %}🟢 优秀{% elif kpi_metrics.quality_score >= 75 %}🟡 良好{% else %}🔴 需改进{% endif %} |
| 客户满意度 | {{kpi_metrics.customer_satisfaction}}/5.0 | {% if kpi_metrics.customer_satisfaction >= 4.5 %}🟢 优秀{% elif kpi_metrics.customer_satisfaction >= 3.5 %}🟡 良好{% else %}🔴 需改进{% endif %} |
| 代码覆盖率 | {{kpi_metrics.code_coverage}}% | {% if kpi_metrics.code_coverage >= 80 %}🟢 优秀{% elif kpi_metrics.code_coverage >= 60 %}🟡 良好{% else %}🔴 需改进{% endif %} |
| Bug密度 | {{kpi_metrics.bug_density}}/千行 | {% if kpi_metrics.bug_density <= 1 %}🟢 优秀{% elif kpi_metrics.bug_density <= 2 %}🟡 良好{% else %}🔴 需改进{% endif %} |

---

## 💰 预算执行情况

### 预算概况

- **项目预算**: ¥{{budget}}万元
- **实际支出**: ¥{{actual_cost}}万元
- **剩余预算**: ¥{{budget_status.remaining}}万元
- **预算使用率**: {{budget_status.usage_rate}}%
- **预算状态**: {% if budget_status.status == '正常' %}🟢{% elif budget_status.status == '警告' %}🟡{% else %}🔴{% endif %} {{budget_status.status}}

### 成本效益分析

- **团队规模**: {{team_size}}人
- **人均成本**: ¥{{team_efficiency.avg_cost_per_person}}万元/人
- **成本控制**: {% if budget_status.usage_rate <= 90 %}成本控制良好，符合预算规划{% elif budget_status.usage_rate <= 100 %}接近预算上限，需要密切关注{% else %}已超出预算，需要采取紧急措施{% endif %}

```
预算使用情况
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
已使用: {{actual_cost}}万 [{% for i in range((budget_status.usage_rate / 5) | int) %}█{% endfor %}{% for i in range(20 - (budget_status.usage_rate / 5) | int) %}░{% endfor %}] {{budget_status.usage_rate}}%
剩余: {{budget_status.remaining}}万
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🎯 项目里程碑

### 里程碑完成情况

{% for milestone in milestones %}
#### {{loop.index}}. {{milestone.name}}

- **计划日期**: {{milestone.planned_date}}
- **实际日期**: {% if milestone.actual_date %}{{milestone.actual_date}}{% else %}进行中{% endif %}
- **状态**: {% if milestone.status == '已完成' %}✅{% elif milestone.status == '进行中' %}🔄{% else %}⏳{% endif %} {{milestone.status}}
- **完成度**: {{milestone.completion}}%
- **延期天数**: {% if milestone.delay_days > 0 %}🔴 {{milestone.delay_days}}天{% elif milestone.delay_days == 0 %}🟢 按时{% else %}{{milestone.delay_days}}天{% endif %}

{% endfor %}

### 里程碑统计

- **总里程碑数**: {{milestones | length}}
- **已完成**: {% set completed = milestones | selectattr('status', 'equalto', '已完成') | list %}{{completed | length}}个
- **进行中**: {% set inprogress = milestones | selectattr('status', 'equalto', '进行中') | list %}{{inprogress | length}}个
- **未开始**: {% set notstarted = milestones | selectattr('status', 'equalto', '未开始') | list %}{{notstarted | length}}个
- **按时完成率**: {{kpi_metrics.on_time_rate}}%

---

## 👥 团队表现

### 团队成员贡献

| 姓名 | 角色 | 完成任务数 | 绩效评分 | 评级 |
|------|------|-----------|---------|------|
{% for member in team_members %}
| {{member.name}} | {{member.role}} | {{member.tasks_completed}} | {{member.performance}}/100 | {% if member.performance >= 90 %}⭐⭐⭐{% elif member.performance >= 80 %}⭐⭐{% else %}⭐{% endif %} |
{% endfor %}

### 团队分析

- **团队规模**: {{team_size}}人（{{team_efficiency.team_level}}）
- **总完成任务**: {% set total_tasks = team_members | sum(attribute='tasks_completed') %}{{total_tasks}}个
- **平均绩效**: {% set avg_perf = (team_members | sum(attribute='performance') / (team_members | length)) | round(1) %}{{avg_perf}}/100
- **团队状态**: {% if avg_perf >= 90 %}🟢 优秀{% elif avg_perf >= 80 %}🟡 良好{% else %}🔴 需改进{% endif %}

---

## 🏆 主要成果

{% for achievement in achievements %}
### {{loop.index}}. {{achievement.title}}

**完成日期**: {{achievement.date}}

**成果描述**:  
{{achievement.description}}

**影响与价值**:  
{{achievement.impact}}

---
{% endfor %}

---

## ⚠️ 风险评估与应对

### 风险清单

{% for risk in risk_assessment %}
#### {{loop.index}}. {{risk.category}}

- **描述**: {{risk.description}}
- **风险等级**: {% if risk.level == '高' %}🔴 高风险{% elif risk.level == '中' %}🟡 中风险{% else %}🟢 低风险{% endif %}
- **应对措施**: {{risk.mitigation}}

{% endfor %}

### 风险分布

- **高风险**: {% set high_risks = risk_assessment | selectattr('level', 'equalto', '高') | list %}{{high_risks | length}}项
- **中风险**: {% set medium_risks = risk_assessment | selectattr('level', 'equalto', '中') | list %}{{medium_risks | length}}项
- **低风险**: {% set low_risks = risk_assessment | selectattr('level', 'equalto', '低') | list %}{{low_risks | length}}项

---

## 📈 下一步计划

### Q4季度工作重点

1. **完成用户验收测试**
   - 时间: 2025年7月底前
   - 责任人: {{project_manager}}
   - 目标: 确保所有功能满足用户需求

2. **系统正式上线**
   - 时间: 2025年8月15日
   - 责任人: 技术负责人
   - 目标: 平滑上线，确保系统稳定运行

3. **性能监控与优化**
   - 持续进行系统性能监控
   - 根据实际运行情况进行优化
   - 确保系统响应时间在SLA范围内

4. **用户培训与支持**
   - 组织用户培训
   - 建立完善的技术支持体系
   - 收集用户反馈，持续改进

### 资源需求

- **人力**: 维持当前团队规模{{team_size}}人
- **预算**: 预计Q4需要追加预算{{(budget * 0.2) | round(0)}}万元
- **时间**: 预计2个月完成所有剩余工作

---

## 📝 总结

### 项目亮点

✅ **进度稳定**: 整体进度{{kpi_metrics.overall_progress}}%，符合项目规划  
✅ **质量优秀**: 质量评分{{kpi_metrics.quality_score}}/100，客户满意度{{kpi_metrics.customer_satisfaction}}/5.0  
✅ **成本可控**: 预算使用率{{budget_status.usage_rate}}%，成本控制良好  
✅ **团队高效**: 团队平均绩效{{avg_perf}}/100，协作顺畅

### 需要关注的问题

⚠️ 部分里程碑存在延期，需要加强进度管控  
⚠️ 核心成员工作饱和度较高，需要合理分配任务  
⚠️ Q4预算可能需要追加，需提前做好规划

### 综合评价

项目整体执行情况**{% if kpi_metrics.overall_progress >= 80 and budget_status.usage_rate <= 100 %}优秀{% elif kpi_metrics.overall_progress >= 60 %}良好{% else %}需改进{% endif %}**，在{{project_manager}}的领导下，团队展现出了良好的执行力和专业素养。通过持续的风险管控和资源优化，项目有望按计划成功交付。

---

## 📎 附录

### 报告信息

- **报告生成时间**: {{report_metadata.generated_at}}
- **报告编制**: {{report_metadata.author}}
- **报告版本**: {{report_metadata.version}}
- **报告ID**: {{report_metadata.report_id}}

### 数据说明

本报告中的所有数据均基于项目管理系统的真实记录，统计周期为{{report_period}}季度（2025年7月1日至2025年9月30日）。

---

*本报告由智能报告生成系统自动生成 | 生成时间: {{report_metadata.generated_at}}*
"""
    
    # 渲染模板
    print("\n📄 开始渲染报告...")
    markdown = template_renderer.render(template_content, context.get_all_variables())
    
    # 输出结果
    print("\n" + "=" * 80)
    print("✅ 生成的完整Markdown报告:")
    print("=" * 80)
    print(markdown)
    print("=" * 80)
    
    # 保存到文件
    output_file = "/data/tao/code/xuqiu/backend/complex_report_output.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    print(f"\n💾 报告已保存到: {output_file}")
    print(f"📊 报告统计:")
    print(f"   - 总字符数: {len(markdown)}")
    print(f"   - 总行数: {len(markdown.splitlines())}")
    print(f"   - 使用变量数: {len(metadata)}")
    print(f"   - 执行批次数: {len(batches)}")


async def example_comprehensive_all_types():
    """示例5: 全类型变量综合示例 - 覆盖所有变量源和SQL ResultMode"""
    print("\n\n" + "=" * 80)
    print("示例5: 全类型变量综合示例（除AI外所有类型）")
    print("=" * 80)
    
    # 用户输入
    user_inputs = {
        "report_title": "2025年销售数据综合分析报告",
        "analyst_name": "数据分析师-张三",
        "department": "销售部",
        "year": 2025,
        "quarter": "Q1",
        "threshold_amount": 50000
    }
    
    metadata = {
        # ==================== 1. USER_INPUT 类型 ====================
        "report_title": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="报告标题",
            required=True
        ),
        
        "analyst_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="分析师姓名",
            required=True
        ),
        
        "department": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="部门",
            required=True
        ),
        
        "year": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="年份",
            required=True
        ),
        
        "quarter": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="季度",
            required=True
        ),
        
        "threshold_amount": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="金额阈值",
            required=True
        ),
        
        # ==================== 2. SYSTEM 类型 ====================
        "report_metadata": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="报告元数据（系统生成）",
            required=True,
            system_config=SystemConfig(
                fields={
                    "report_id": {"generator": "uuid"},
                    "generated_at": {"generator": "datetime", "format": "%Y-%m-%d %H:%M:%S"},
                    "generated_date": {"generator": "datetime", "format": "%Y年%m月%d日"},
                    "version": {"value": "3.0.0"}
                }
            )
        ),
        
        "static_config": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="静态配置",
            required=True,
            system_config=SystemConfig(
                fields={
                    "company_name": {"value": "某某科技有限公司"},
                    "report_type": {"value": "销售数据分析"},
                    "currency": {"value": "CNY"}
                }
            )
        ),
        
        # ==================== 3. API 类型 ====================
        # API - 基础数据类型
        "api_basic_sales": VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="基础销售数据（API - 混合基础类型）",
            required=False,
            default={
                "total_sales": 156780.50,
                "units_sold": 1200,
                "is_active": True,
                "salesperson": "John Doe (示例数据)"
            },
            api_config=ApiConfig(
                endpoint="http://10.10.20.10:5000/api/sales/basic",
                method="GET",
                response_mapping={},  # 直接使用整个响应
                timeout=10
            )
        ),
        
        # API - 数组数据
        "api_array_sales": VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="数组销售数据（API - 基础类型数组）",
            required=False,
            default={
                "daily_sales": [1250.0, 1320.5, 1180.75, 2900.25, 1750.0],
                "top_products": ["Laptop (示例)", "Mouse (示例)", "Keyboard (示例)", "Monitor (示例)"]
            },
            api_config=ApiConfig(
                endpoint="http://10.10.20.10:5000/api/sales/array",
                method="GET",
                response_mapping={},
                timeout=10
            )
        ),
        
        # API - 对象数组
        "api_product_sales": VariableMetadata(
            type="array",
            source=VariableSource.API,
            description="产品销售列表（API - 对象数组）",
            required=False,
            default=[
                {
                    "product": "Laptop (示例)",
                    "price": 999.99,
                    "quantity": 15,
                    "features": ["8GB RAM", "256GB SSD", "Intel i5"]
                },
                {
                    "product": "Wireless Mouse (示例)",
                    "price": 25.50,
                    "quantity": 43,
                    "features": ["2.4GHz", "DPI Switch", "Ergonomic"]
                }
            ],
            api_config=ApiConfig(
                endpoint="http://10.10.20.10:5000/api/sales/object-array",
                method="GET",
                response_mapping={},
                timeout=10
            )
        ),
        
        # API - 嵌套对象
        "api_nested_report": VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="区域季度报告（API - 嵌套对象）",
            required=False,
            default={
                "region": "North America (示例)",
                "quarterly_report": {
                    "q1": {
                        "revenue": 50000,
                        "growth_rate": 0.15,
                        "top_performer": "Alice Smith"
                    },
                    "q2": {
                        "revenue": 75000,
                        "growth_rate": 0.25,
                        "top_performer": "Bob Johnson"
                    }
                },
                "departments": ["Sales", "Marketing", "Support"]
            },
            api_config=ApiConfig(
                endpoint="http://10.10.20.10:5000/api/sales/nested-object",
                method="GET",
                response_mapping={},
                timeout=10
            )
        ),
        
        # API - 复杂混合数据
        "api_complex_data": VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="复杂营销数据（API - 深度嵌套）",
            required=False,
            default={
                "success": True,
                "timestamp": "2024-01-15T10:30:00Z (示例)",
                "summary": {
                    "total_revenue": 250000.75,
                    "active_campaigns": 5,
                    "conversion_rate": 0.23
                },
                "campaigns": [
                    {
                        "id": 1,
                        "name": "Summer Sale (示例)",
                        "discounts": [0.1, 0.15, 0.2],
                        "target_audience": {
                            "age_range": [18, 45],
                            "regions": ["US", "CA", "MX"]
                        }
                    },
                    {
                        "id": 2,
                        "name": "Holiday Special (示例)",
                        "discounts": [0.25, 0.3],
                        "target_audience": {
                            "age_range": [25, 60],
                            "regions": ["US", "UK"]
                        }
                    }
                ]
            },
            api_config=ApiConfig(
                endpoint="http://10.10.20.10:5000/api/sales/complex",
                method="GET",
                response_mapping={},
                timeout=10
            )
        ),
        
        # ==================== 4. SQL 类型 - 所有5种ResultMode ====================
        # 注意：这些SQL变量展示配置，但需要数据库连接才能真实执行
        
        # SQL - FIRST_ROW 模式
        "sql_first_row_customer": VariableMetadata(
            type="object",
            source=VariableSource.SQL,
            description="VIP客户信息（SQL - FIRST_ROW返回单个对象）",
            required=False,
            default={"id": 1001, "name": "示例客户", "level": "VIP", "total_purchase": 125000},
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT 
                        customer_id as id,
                        customer_name as name,
                        customer_level as level,
                        total_purchase_amount as total_purchase
                    FROM customers
                    WHERE customer_id = 1001
                """,
                timeout=10,
                result_mode=SqlResultMode.FIRST_ROW
            )
        ),
        
        # SQL - ALL_ROWS 模式
        "sql_all_rows_orders": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="所有订单列表（SQL - ALL_ROWS返回数组）",
            required=False,
            default=[
                {"order_id": "ORD001", "amount": 1250.0, "status": "completed"},
                {"order_id": "ORD002", "amount": 3500.5, "status": "completed"},
                {"order_id": "ORD003", "amount": 890.0, "status": "pending"}
            ],
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT 
                        order_id,
                        order_amount as amount,
                        order_status as status
                    FROM orders
                    WHERE order_date >= '2025-01-01'
                    ORDER BY order_date DESC
                    LIMIT 10
                """,
                timeout=10,
                result_mode=SqlResultMode.ALL_ROWS
            )
        ),
        
        # SQL - FIRST_VALUE 模式（返回标量 - 数值）
        "sql_first_value_revenue": VariableMetadata(
            type="number",
            source=VariableSource.SQL,
            description="总收入（SQL - FIRST_VALUE返回标量数值）",
            required=False,
            default=256780.50,
            dependencies=["threshold_amount"],
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT SUM(order_amount) as total_revenue
                    FROM orders
                    WHERE order_status = 'completed'
                      AND order_amount > {{threshold_amount}}
                """,
                parameters=["threshold_amount"],
                timeout=10,
                result_mode=SqlResultMode.FIRST_VALUE
            )
        ),
        
        # SQL - FIRST_VALUE 模式（返回标量 - 整数计数）
        "sql_first_value_count": VariableMetadata(
            type="number",
            source=VariableSource.SQL,
            description="订单总数（SQL - FIRST_VALUE返回标量整数）",
            required=False,
            default=1547,
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT COUNT(*) as order_count
                    FROM orders
                    WHERE order_date >= '2025-01-01'
                """,
                timeout=10,
                result_mode=SqlResultMode.FIRST_VALUE
            )
        ),
        
        # SQL - FIRST_COLUMN 模式（返回单列数组 - 数值）
        "sql_first_column_amounts": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="订单金额列表（SQL - FIRST_COLUMN返回数值数组）",
            required=False,
            default=[1250.0, 3500.5, 890.0, 2100.75, 5600.25],
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT order_amount
                    FROM orders
                    WHERE order_status = 'completed'
                    ORDER BY order_date DESC
                    LIMIT 20
                """,
                timeout=10,
                result_mode=SqlResultMode.FIRST_COLUMN
            )
        ),
        
        # SQL - FIRST_COLUMN 模式（返回单列数组 - 字符串）
        "sql_first_column_products": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="产品名称列表（SQL - FIRST_COLUMN返回字符串数组）",
            required=False,
            default=["笔记本电脑", "无线鼠标", "机械键盘", "显示器", "耳机"],
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT DISTINCT product_name
                    FROM order_items
                    WHERE quantity > 0
                    ORDER BY product_name
                """,
                timeout=10,
                result_mode=SqlResultMode.FIRST_COLUMN
            )
        ),
        
        # SQL - AUTO 模式（type=object，自动判断为FIRST_ROW）
        "sql_auto_summary": VariableMetadata(
            type="object",
            source=VariableSource.SQL,
            description="销售汇总（SQL - AUTO模式自动判断）",
            required=False,
            default={
                "total_revenue": 256780.50,
                "total_orders": 1547,
                "avg_order_value": 166.02,
                "top_product": "笔记本电脑"
            },
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT 
                        SUM(order_amount) as total_revenue,
                        COUNT(*) as total_orders,
                        AVG(order_amount) as avg_order_value,
                        (SELECT product_name FROM order_items 
                         GROUP BY product_name 
                         ORDER BY SUM(quantity) DESC LIMIT 1) as top_product
                    FROM orders
                    WHERE order_date >= '2025-01-01'
                """,
                timeout=10,
                result_mode=SqlResultMode.AUTO
            )
        ),
        
        # SQL - AUTO 模式（type=array，自动判断为ALL_ROWS）
        "sql_auto_categories": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="分类销售统计（SQL - AUTO模式返回数组）",
            required=False,
            default=[
                {"category": "电脑配件", "revenue": 125000, "count": 450},
                {"category": "办公用品", "revenue": 78500, "count": 890},
                {"category": "网络设备", "revenue": 53280, "count": 207}
            ],
            sql_config=SqlConfig(
                connection="sales_db",
                query="""
                    SELECT 
                        category,
                        SUM(order_amount) as revenue,
                        COUNT(*) as count
                    FROM orders o
                    JOIN order_items oi ON o.order_id = oi.order_id
                    GROUP BY category
                    ORDER BY revenue DESC
                """,
                timeout=10,
                result_mode=SqlResultMode.AUTO
            )
        )
    }
    
    # 创建执行上下文
    context = ExecutionContext(
        task_id="comprehensive_demo",
        template_id="all_types_template",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # 执行调度器
    scheduler = ExecutionScheduler()
    
    # 显示执行计划
    dag = scheduler.build_dag(metadata)
    batches = scheduler.get_execution_batches(dag)
    
    print("\n📋 执行计划（变量依赖分批）:")
    for i, batch in enumerate(batches, 1):
        print(f"  批次 {i}: {', '.join(batch)}")
    
    print(f"\n📊 变量类型统计:")
    source_counts = {}
    for var_name, var_meta in metadata.items():
        source = var_meta.source.value
        source_counts[source] = source_counts.get(source, 0) + 1
    for source, count in source_counts.items():
        print(f"  • {source}: {count}个")
    
    print("\n⚙️  开始执行所有变量...")
    results = await scheduler.execute_all(context)
    
    # 显示执行结果
    print("\n✅ 变量执行结果:")
    success_count = 0
    failed_count = 0
    for var_name, result in results.items():
        if result.status == VariableStatus.SUCCESS:
            status_icon = "✅"
            success_count += 1
        else:
            status_icon = "❌"
            failed_count += 1
        
        source = metadata[var_name].source.value
        print(f"  {status_icon} [{source:12s}] {var_name:30s} ({result.duration_ms}ms)")
        
        # 如果失败，显示错误
        if result.status != VariableStatus.SUCCESS:
            print(f"      错误: {result.error}")
    
    print(f"\n📈 执行统计: 成功 {success_count}个, 失败 {failed_count}个")
    
    # 生成综合报告模板
    template_content = """# {{report_title}}

**分析师**: {{analyst_name}}  
**部门**: {{department}}  
**年份**: {{year}}年  
**季度**: {{quarter}}  
**报告ID**: {{report_metadata.report_id}}  
**生成时间**: {{report_metadata.generated_at}}

---

## 📌 报告说明

本报告由「{{static_config.company_name}}」的{{department}}生成，涵盖{{year}}年{{quarter}}季度的销售数据分析。
报告类型：{{static_config.report_type}}，货币单位：{{static_config.currency}}。

---

## 💰 基础销售数据（API - 基础类型）

**来源**: Flask API `/api/sales/basic`

- **总销售额**: ¥{{api_basic_sales.total_sales}} 元
- **销售数量**: {{api_basic_sales.units_sold}} 件
- **活跃状态**: {% if api_basic_sales.is_active %}✅ 活跃{% else %}❌ 不活跃{% endif %}
- **销售员**: {{api_basic_sales.salesperson}}

---

## 📊 每日销售数据（API - 数组类型）

**来源**: Flask API `/api/sales/array`

### 每日销售额趋势
{% for amount in api_array_sales.daily_sales %}
- 第{{loop.index}}天: ¥{{amount}}元
{% endfor %}

### 热销产品Top列表
{% for product in api_array_sales.top_products %}
{{loop.index}}. {{product}}
{% endfor %}

---

## 🛒 产品销售详情（API - 对象数组）

**来源**: Flask API `/api/sales/object-array`

| 产品 | 单价 | 数量 | 特性 |
|------|------|------|------|
{% for item in api_product_sales %}
| {{item.product}} | ${{item.price}} | {{item.quantity}} | {{item.features | join(', ')}} |
{% endfor %}

**产品总数**: {{api_product_sales | length}}个

---

## 🌎 区域季度报告（API - 嵌套对象）

**来源**: Flask API `/api/sales/nested-object`

**区域**: {{api_nested_report.region}}

### Q1季度表现
- **收入**: ${{api_nested_report.quarterly_report.q1.revenue}}
- **增长率**: {{(api_nested_report.quarterly_report.q1.growth_rate * 100)}}%
- **最佳员工**: {{api_nested_report.quarterly_report.q1.top_performer}}

### Q2季度表现
- **收入**: ${{api_nested_report.quarterly_report.q2.revenue}}
- **增长率**: {{(api_nested_report.quarterly_report.q2.growth_rate * 100)}}%
- **最佳员工**: {{api_nested_report.quarterly_report.q2.top_performer}}

**涉及部门**: {{api_nested_report.departments | join(' / ')}}

---

## 🎯 营销活动数据（API - 复杂嵌套）

**来源**: Flask API `/api/sales/complex`

**数据时间戳**: {{api_complex_data.timestamp}}  
**状态**: {% if api_complex_data.success %}✅ 成功{% else %}❌ 失败{% endif %}

### 营销摘要
- **总收入**: ${{api_complex_data.summary.total_revenue}}
- **活跃活动数**: {{api_complex_data.summary.active_campaigns}}
- **转化率**: {{(api_complex_data.summary.conversion_rate * 100)}}%

### 活动详情
{% for campaign in api_complex_data.campaigns %}
#### {{loop.index}}. {{campaign.name}} (ID: {{campaign.id}})
- **折扣力度**: {{campaign.discounts | join('%, ') | replace('0.', '') }}%
- **目标年龄**: {{campaign.target_audience.age_range[0]}}-{{campaign.target_audience.age_range[1]}}岁
- **目标区域**: {{campaign.target_audience.regions | join(', ')}}
{% endfor %}

---

## 🗄️ SQL数据分析（5种ResultMode演示）

### 1️⃣ FIRST_ROW - VIP客户信息

**SQL**: 返回第一行作为对象

- **客户ID**: {{sql_first_row_customer.id}}
- **客户名称**: {{sql_first_row_customer.name}}
- **客户等级**: {{sql_first_row_customer.level}}
- **累计消费**: ¥{{sql_first_row_customer.total_purchase}}

### 2️⃣ ALL_ROWS - 订单列表

**SQL**: 返回所有行作为数组

| 订单号 | 金额 | 状态 |
|--------|------|------|
{% for order in sql_all_rows_orders %}
| {{order.order_id}} | ¥{{order.amount}} | {{order.status}} |
{% endfor %}

**订单总数**: {{sql_all_rows_orders | length}}笔

### 3️⃣ FIRST_VALUE - 聚合统计

**SQL**: 返回第一行第一列的标量值

- **总收入** (金额>¥{{threshold_amount}}): ¥{{sql_first_value_revenue}}
- **订单总数**: {{sql_first_value_count}}笔
- **平均订单金额**: ¥{{(sql_first_value_revenue / sql_first_value_count) | round(2)}}

### 4️⃣ FIRST_COLUMN - 列数据提取

**SQL**: 返回第一列的所有值

#### 订单金额分布（前5条）
{% for amount in sql_first_column_amounts[:5] %}
- ¥{{amount}}
{% endfor %}
**金额数据点**: {{sql_first_column_amounts | length}}个

#### 产品名称列表
{% for product in sql_first_column_products %}
- {{product}}
{% endfor %}
**产品种类**: {{sql_first_column_products | length}}种

### 5️⃣ AUTO - 自动判断模式

**SQL (对象)**: 自动判断为FIRST_ROW

- **总收入**: ¥{{sql_auto_summary.total_revenue}}
- **总订单**: {{sql_auto_summary.total_orders}}笔
- **平均订单**: ¥{{sql_auto_summary.avg_order_value}}
- **热销产品**: {{sql_auto_summary.top_product}}

**SQL (数组)**: 自动判断为ALL_ROWS

| 分类 | 收入 | 订单数 |
|------|------|--------|
{% for cat in sql_auto_categories %}
| {{cat.category}} | ¥{{cat.revenue}} | {{cat.count}} |
{% endfor %}

---

## 📋 变量类型汇总

本报告使用了以下变量源类型：

| 类型 | 说明 | 数量 |
|------|------|------|
| USER_INPUT | 用户输入变量 | 6个 |
| SYSTEM | 系统生成变量 | 2个 |
| API | API调用变量 | 5个 |
| SQL | SQL查询变量 | 8个 |

### SQL ResultMode详解

| ResultMode | 返回类型 | 用途 | 示例变量 |
|------------|---------|------|---------|
| FIRST_ROW | object | 单条记录详情 | sql_first_row_customer |
| ALL_ROWS | array | 多条记录列表 | sql_all_rows_orders |
| FIRST_VALUE | number/string | 聚合统计值 | sql_first_value_revenue |
| FIRST_COLUMN | array | 单列值列表 | sql_first_column_amounts |
| AUTO | 自动判断 | 根据type自动选择 | sql_auto_summary |

---

## ✅ 总结

本报告成功演示了智能报告生成系统的全部变量类型（除AI外）：

✅ **用户输入** - 灵活的表单输入  
✅ **系统生成** - UUID、时间戳、常量  
✅ **API调用** - RESTful接口集成（5个API演示）  
✅ **SQL查询** - 5种ResultMode全覆盖（8个SQL演示）

---

*报告生成时间: {{report_metadata.generated_at}} | 版本: {{report_metadata.version}}*
"""
    
    # 渲染报告
    print("\n📄 开始渲染综合报告...")
    markdown = template_renderer.render(template_content, context.get_all_variables())
    
    # 输出报告
    print("\n" + "=" * 80)
    print("✅ 生成的综合报告预览（前50行）:")
    print("=" * 80)
    lines = markdown.split('\n')
    for line in lines[:50]:
        print(line)
    if len(lines) > 50:
        print(f"\n... (还有 {len(lines) - 50} 行)")
    print("=" * 80)
    
    # 保存报告
    output_file = "/data/tao/code/xuqiu/backend/comprehensive_report_output.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    print(f"\n💾 完整报告已保存到: {output_file}")
    print(f"\n📊 报告统计:")
    print(f"   - 总字符数: {len(markdown)}")
    print(f"   - 总行数: {len(lines)}")
    print(f"   - 总变量数: {len(metadata)}")
    print(f"   - 执行批次: {len(batches)}")
    print(f"   - 成功变量: {success_count}")
    print(f"   - 失败变量: {failed_count}")


async def example_ai_generation():
    """示例6: AI生成变量测试 - 使用硅基流动GLM模型"""
    print("\n\n" + "=" * 80)
    print("示例6: AI生成变量测试（硅基流动 THUDM/GLM-Z1-9B-0414）")
    print("=" * 80)
    
    # 获取API配置
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    
    print(f"\n🔑 API配置:")
    print(f"   API Key: {api_key[:10]}..." if api_key else "   API Key: 未配置")
    print(f"   API Base: {api_base}" if api_base else "   API Base: 未配置")
    
    if not api_key:
        print("\n❌ 错误: 未找到OPENAI_API_KEY环境变量")
        return
    
    # 用户输入
    user_inputs = {
        "report_title": "2025年Q1技术分析报告",
        "company_name": "某某科技有限公司",
        "analysis_focus": "人工智能",
        "target_audience": "技术团队"
    }
    
    # 定义变量元数据
    metadata = {
        # 用户输入
        "report_title": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="报告标题",
            required=True
        ),
        
        "company_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="公司名称",
            required=True
        ),
        
        "analysis_focus": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="分析焦点",
            required=True
        ),
        
        "target_audience": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="目标受众",
            required=True
        ),
        
        # 系统变量
        "report_metadata": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="报告元数据",
            required=True,
            system_config=SystemConfig(
                fields={
                    "report_id": {"generator": "uuid"},
                    "generated_at": {"generator": "datetime", "format": "%Y-%m-%d %H:%M:%S"},
                    "version": {"value": "1.0.0"}
                }
            )
        ),
        
        # AI生成变量1: 技术趋势分析
        "tech_trends": VariableMetadata(
            type="array",
            source=VariableSource.AI_GENERATION,
            description="技术趋势分析",
            required=True,
            dependencies=["analysis_focus"],
            ai_config=AiConfig(
                model="THUDM/GLM-Z1-9B-0414",
                prompt_template="""请分析{{analysis_focus}}领域的技术趋势。

要求：
1. 列出5个主要技术趋势
2. 每个趋势包含：名称、描述、影响力评分(1-10)、预计成熟时间

请返回JSON数组格式。""",
                temperature=0.7,
                max_tokens=3000
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "impact_score": {"type": "number"},
                        "maturity_timeline": {"type": "string"}
                    },
                    "required": ["name", "description", "impact_score", "maturity_timeline"]
                }
            }
        ),
        
        # AI生成变量2: 市场分析
        "market_analysis": VariableMetadata(
            type="object",
            source=VariableSource.AI_GENERATION,
            description="市场分析",
            required=True,
            dependencies=["analysis_focus", "company_name"],
            ai_config=AiConfig(
                model="THUDM/GLM-Z1-9B-0414",
                prompt_template="""为「{{company_name}}」分析{{analysis_focus}}领域的市场状况。

要求：
1. 市场规模（市场总值、年增长率）
2. 竞争态势（竞争强度、主要竞争者数量）
3. 机会与挑战（各列出3点）
4. 总体评估

请返回JSON对象格式。""",
                temperature=0.6,
                max_tokens=2500
            ),
            schema={
                "type": "object",
                "properties": {
                    "market_size": {
                        "type": "object",
                        "properties": {
                            "total_value": {"type": "string"},
                            "growth_rate": {"type": "string"}
                        }
                    },
                    "competition": {
                        "type": "object",
                        "properties": {
                            "intensity": {"type": "string"},
                            "major_players_count": {"type": "number"}
                        }
                    },
                    "opportunities": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "challenges": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "overall_assessment": {"type": "string"}
                },
                "required": ["market_size", "competition", "opportunities", "challenges", "overall_assessment"]
            }
        ),
        
        # AI生成变量3: 行动建议
        "action_recommendations": VariableMetadata(
            type="array",
            source=VariableSource.AI_GENERATION,
            description="行动建议",
            required=True,
            dependencies=["analysis_focus", "target_audience"],
            ai_config=AiConfig(
                model="THUDM/GLM-Z1-9B-0414",
                prompt_template="""基于{{analysis_focus}}领域的当前发展趋势和市场状况，为{{target_audience}}提供行动建议。

要求：
1. 提供5条具体的行动建议
2. 每条建议包含：标题、详细描述、优先级(高/中/低)、预期效果、实施时间框架
3. 建议要具体可执行，并考虑技术可行性和市场需求

请返回JSON数组格式。""",
                temperature=0.7,
                max_tokens=3000
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": ["高", "中", "低"]},
                        "expected_outcome": {"type": "string"},
                        "timeframe": {"type": "string"}
                    },
                    "required": ["title", "description", "priority", "expected_outcome", "timeframe"]
                }
            }
        )
    }
    
    # 创建执行上下文
    context = ExecutionContext(
        task_id="ai_demo_001",
        template_id="ai_template_001",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # 创建调度器（传入API密钥和base）
    scheduler = ExecutionScheduler(
        openai_api_key=api_key,
        openai_api_base=api_base
    )
    
    # 显示执行计划
    dag = scheduler.build_dag(metadata)
    batches = scheduler.get_execution_batches(dag)
    
    print("\n📋 执行计划（按批次）:")
    for i, batch in enumerate(batches, 1):
        print(f"  批次 {i}: {', '.join(batch)}")
    
    print("\n⚙️  开始执行所有变量...")
    print("   (AI生成可能需要10-30秒，请耐心等待...)\n")
    
    results = await scheduler.execute_all(context)
    
    # 显示执行结果
    print("\n✅ 变量执行结果:")
    success_count = 0
    failed_count = 0
    
    for var_name, result in results.items():
        if result.status == VariableStatus.SUCCESS:
            status_icon = "✅"
            success_count += 1
        else:
            status_icon = "❌"
            failed_count += 1
        
        source = metadata[var_name].source.value
        print(f"  {status_icon} [{source:15s}] {var_name:30s} ({result.duration_ms}ms)")
        
        # 如果失败，显示错误
        if result.status != VariableStatus.SUCCESS:
            print(f"      错误: {result.error}")
    
    print(f"\n📈 执行统计: 成功 {success_count}个, 失败 {failed_count}个")
    
    # 如果有AI变量成功，显示部分结果
    if success_count > 0:
        print("\n🤖 AI生成结果预览:")
        
        if "tech_trends" in context.variables:
            trends = context.get_variable("tech_trends")
            print(f"\n  📊 技术趋势 (共{len(trends)}条):")
            for i, trend in enumerate(trends[:2], 1):  # 只显示前2条
                print(f"    {i}. {trend.get('name', 'N/A')}")
                print(f"       影响力: {trend.get('impact_score', 0)}/10")
        
        if "market_analysis" in context.variables:
            market = context.get_variable("market_analysis")
            print(f"\n  💼 市场分析:")
            if "market_size" in market:
                print(f"    市场规模: {market['market_size'].get('total_value', 'N/A')}")
                print(f"    增长率: {market['market_size'].get('growth_rate', 'N/A')}")
        
        if "action_recommendations" in context.variables:
            actions = context.get_variable("action_recommendations")
            print(f"\n  🎯 行动建议 (共{len(actions)}条):")
            for i, action in enumerate(actions[:2], 1):  # 只显示前2条
                print(f"    {i}. {action.get('title', 'N/A')} [优先级: {action.get('priority', 'N/A')}]")
    
    # 生成报告模板
    template_content = """# {{report_title}}

**公司**: {{company_name}}  
**分析焦点**: {{analysis_focus}}  
**目标受众**: {{target_audience}}  
**报告ID**: {{report_metadata.report_id}}  
**生成时间**: {{report_metadata.generated_at}}

---

## 🚀 技术趋势分析

{% for trend in tech_trends %}
### {{loop.index}}. {{trend.name}}

**描述**: {{trend.description}}

**影响力评分**: {{trend.impact_score}}/10  
**预计成熟时间**: {{trend.maturity_timeline}}

---
{% endfor %}

## 💼 市场分析

### 市场规模
- **市场总值**: {{market_analysis.market_size.total_value}}
- **年增长率**: {{market_analysis.market_size.growth_rate}}

### 竞争态势
- **竞争强度**: {{market_analysis.competition.intensity}}
- **主要竞争者**: {{market_analysis.competition.major_players_count}}家

### 机会
{% for opportunity in market_analysis.opportunities %}
- {{opportunity}}
{% endfor %}

### 挑战
{% for challenge in market_analysis.challenges %}
- {{challenge}}
{% endfor %}

### 总体评估
{{market_analysis.overall_assessment}}

---

## 🎯 行动建议

{% for action in action_recommendations %}
### {{loop.index}}. {{action.title}}

**优先级**: {% if action.priority == '高' %}🔴{% elif action.priority == '中' %}🟡{% else %}🟢{% endif %} {{action.priority}}

**描述**: {{action.description}}

**预期效果**: {{action.expected_outcome}}

**实施时间**: {{action.timeframe}}

---
{% endfor %}

## 📝 结语

本报告由AI智能生成系统自动生成，使用硅基流动提供的 **THUDM/GLM-Z1-9B-0414** 模型。

---

*报告生成时间: {{report_metadata.generated_at}} | 版本: {{report_metadata.version}}*
"""
    
    # 渲染报告
    if success_count == len(metadata):
        print("\n📄 开始渲染AI报告...")
        markdown = template_renderer.render(template_content, context.get_all_variables())
        
        # 保存报告
        output_file = "/data/tao/code/xuqiu/backend/ai_report_output.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        print(f"\n💾 完整报告已保存到: {output_file}")
        print(f"\n📊 报告统计:")
        print(f"   - 总字符数: {len(markdown)}")
        print(f"   - 总行数: {len(markdown.splitlines())}")
        print(f"   - AI生成变量: 3个")
        
        # 显示报告预览
        print("\n" + "=" * 80)
        print("📄 AI报告预览（前40行）:")
        print("=" * 80)
        lines = markdown.split('\n')
        for line in lines[:40]:
            print(line)
        if len(lines) > 40:
            print(f"\n... (还有 {len(lines) - 40} 行)")
        print("=" * 80)
    else:
        print("\n⚠️  部分变量执行失败，跳过报告生成")


async def main():
    """主函数"""
    # 运行示例1
    # await example_simple_report()
    
    # 运行示例2
    # await example_with_dependencies()
    
    # 运行示例3 - SQL ResultMode完整示例
    # await example_sql_result_modes()
    
    # 运行示例4 - 复杂真实报告
    # await example_complex_real_report()
    
    # 运行示例5 - 全类型综合示例
    # await example_comprehensive_all_types()
    
    # 运行示例6 - AI生成示例
    await example_ai_generation()
    
    print("\n" + "=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

