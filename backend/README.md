# Markdown 报告自动生成平台 - 后端服务 (P0 核心组件)

## 项目概述

本项目实现了基于 Jinja2 模板和多源数据注入的 Markdown 报告自动生成系统的后端核心服务组件（P0优先级）。

## 核心功能

### ✅ 已实现的 P0 组件

1. **执行上下文管理 (ExecutionContext)**
   - 变量存储与获取
   - 依赖关系检查
   - 字符串插值（{{variable}}）
   - 上下文快照

2. **变量执行器 (Variable Executors)**
   - `UserInputExecutor`: 处理用户输入变量
   - `SystemExecutor`: 生成系统变量（时间戳、UUID、常量）
   - `SqlExecutor`: 执行SQL查询（未测试，需要数据库连接）
   - `ApiExecutor`: 调用外部API（未测试，需要实际API）
   - `AiExecutor`: LangChain集成的AI生成（未测试，需要OpenAI API Key）

3. **数据源连接器 (Connectors)**
   - `DatabaseConnector`: SQLAlchemy数据库连接池管理
   - `ApiConnector`: HTTP客户端（支持GET/POST/PUT/DELETE）

4. **模板渲染器 (TemplateRenderer)**
   - Jinja2 SandboxedEnvironment
   - 自定义过滤器（JSON）
   - 模板验证
   - Markdown后处理

5. **执行调度器 (ExecutionScheduler)**
   - DAG（有向无环图）构建
   - 依赖分析与拓扑排序
   - 批次并行执行
   - 进度回调支持

## 项目结构

```
backend/
├── app/
│   ├── core/                    # 核心数据模型和异常
│   │   ├── models.py           # Pydantic数据模型
│   │   └── exceptions.py       # 自定义异常类
│   ├── services/               # 服务层
│   │   ├── context.py          # 执行上下文管理
│   │   ├── renderer.py         # 模板渲染器
│   │   └── scheduler.py        # 执行调度器
│   ├── connectors/             # 数据源连接器
│   │   ├── database.py         # 数据库连接器
│   │   └── api.py              # API连接器
│   └── executors/              # 变量执行器
│       ├── base.py             # 基类
│       ├── user_input.py       # 用户输入
│       ├── system.py           # 系统变量
│       ├── sql.py              # SQL查询
│       ├── api.py              # API调用
│       └── ai.py               # AI生成
├── tests/                      # 测试套件
│   ├── test_context.py         # 上下文测试
│   ├── test_executors.py       # 执行器测试
│   ├── test_renderer.py        # 渲染器测试
│   ├── test_scheduler.py       # 调度器测试
│   └── test_integration.py     # 集成测试
├── requirements.txt            # Python依赖
├── pytest.ini                  # Pytest配置
└── README.md                   # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_context.py -v

# 运行集成测试并查看输出
pytest tests/test_integration.py -v -s
```

### 3. 测试结果

✅ **21个测试全部通过**

```
tests/test_context.py::test_context_creation PASSED
tests/test_context.py::test_set_and_get_variable PASSED
tests/test_context.py::test_interpolate_string PASSED
tests/test_context.py::test_interpolate_dict PASSED
tests/test_context.py::test_dependencies PASSED
tests/test_executors.py::test_user_input_executor PASSED
tests/test_executors.py::test_user_input_with_default PASSED
tests/test_executors.py::test_system_executor_datetime PASSED
tests/test_executors.py::test_system_executor_uuid PASSED
tests/test_executors.py::test_system_executor_constant PASSED
tests/test_integration.py::test_complete_report_generation PASSED
tests/test_integration.py::test_dependency_resolution PASSED
tests/test_renderer.py::test_simple_rendering PASSED
tests/test_renderer.py::test_conditional_rendering PASSED
tests/test_renderer.py::test_loop_rendering PASSED
tests/test_renderer.py::test_json_filter PASSED
tests/test_renderer.py::test_template_validation PASSED
tests/test_scheduler.py::test_build_dag_simple PASSED
tests/test_scheduler.py::test_build_dag_circular_dependency PASSED
tests/test_scheduler.py::test_get_execution_batches PASSED
tests/test_scheduler.py::test_execute_all PASSED
```

## 使用示例

### 完整的报告生成流程

```python
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import VariableMetadata, VariableSource, SystemConfig

# 1. 定义变量元数据
metadata = {
    "report_title": VariableMetadata(
        type="string",
        source=VariableSource.USER_INPUT,
        description="报告标题",
        required=True
    ),
    "generation_info": VariableMetadata(
        type="object",
        source=VariableSource.SYSTEM,
        description="生成信息",
        required=True,
        system_config=SystemConfig(
            fields={
                "timestamp": {"generator": "datetime", "format": "%Y-%m-%d %H:%M:%S"},
                "report_id": {"generator": "uuid"}
            }
        )
    )
}

# 2. 创建执行上下文
context = ExecutionContext(
    task_id="task_123",
    template_id="tpl_456",
    user_inputs={"report_title": "Q3项目总结"},
    metadata=metadata
)

# 3. 执行所有变量
scheduler = ExecutionScheduler()
results = await scheduler.execute_all(context)

# 4. 渲染模板
template = """# {{report_title}}

**生成时间**: {{generation_info.timestamp}}
**报告ID**: {{generation_info.report_id}}
"""

markdown = template_renderer.render(template, context.get_all_variables())
print(markdown)
```

### 输出示例

```markdown
# Q3项目总结

**生成时间**: 2025-10-13 13:44:58
**报告ID**: 73058086-14fe-4582-a4e2-84f0a179b462
```

## 核心设计特性

### 1. 依赖管理（DAG）

系统自动分析变量依赖关系，构建有向无环图（DAG），并按拓扑顺序执行：

```python
# 变量定义
var1: 无依赖
var2: 无依赖
var3: 依赖 [var1, var2]

# 自动分批执行
批次1: [var1, var2]  # 并行执行
批次2: [var3]        # 等待批次1完成后执行
```

### 2. 错误处理与降级

- 变量执行失败时自动使用 `default` 值
- 必需变量失败时停止执行
- 详细的错误信息和执行时长统计

### 3. 字符串插值

支持在配置中引用其他变量：

```python
# SQL查询中使用变量
query: "SELECT * FROM users WHERE id = {{user_id}}"

# API URL中使用变量
endpoint: "https://api.example.com/projects/{{project_id}}/tasks"

# AI Prompt中使用变量
prompt: "基于以下信息生成分析：{{project_info}}"
```

### 4. 类型转换

自动进行基本类型转换：
- `string`: 字符串
- `number`: 数字（整数/浮点）
- `boolean`: 布尔值
- `array`: 数组
- `object`: 对象

## 技术栈

- **Python**: 3.11+
- **框架**: Pydantic 2.x
- **模板引擎**: Jinja2 (Sandboxed)
- **数据库**: SQLAlchemy
- **HTTP客户端**: httpx
- **AI集成**: LangChain + OpenAI
- **图算法**: NetworkX
- **测试**: pytest + pytest-asyncio

## 下一步开发（P1功能）

根据《模块说明.md》，P1阶段包括：

1. **缓存机制**: Redis缓存（API/AI结果）
2. **数据库连接管理**: 动态配置与健康检查
3. **对象存储**: S3/MinIO集成
4. **任务队列**: Celery/RQ异步执行
5. **重试策略**: 指数退避与幂等性
6. **成本统计**: Token使用与成本估算
7. **日志持久化**: 详细的执行日志存储

## 测试覆盖率

当前测试覆盖了：
- ✅ 上下文管理（5个测试）
- ✅ 变量执行器（5个测试）
- ✅ 模板渲染器（5个测试）
- ✅ 调度器（4个测试）
- ✅ 集成测试（2个测试）

## 注意事项

1. **AI功能需要API Key**: 设置环境变量 `OPENAI_API_KEY`
2. **SQL功能需要数据库**: 使用 `db_connector.register_connection()` 注册连接
3. **Schema警告**: Pydantic的 `schema` 字段名与父类冲突，但不影响功能
4. **Python版本**: 推荐使用 Python 3.11 或 3.12

## 贡献与反馈

本项目为MVP阶段的P0核心组件实现。如有问题或建议，请参考《模块说明.md》中的架构设计。

