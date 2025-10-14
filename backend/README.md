# Markdown 报告自动生成平台 - 后端服务

## 项目概述

本项目实现了基于 Jinja2 模板和多源数据注入的 Markdown 报告自动生成系统的**完整后端系统**，包括核心服务组件和REST API接口（P0阶段）。

## 核心功能

### ✅ P0 核心组件（已完成）

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

### ✅ P0 REST API（已完成）

6. **模板管理 API**
   - 模板CRUD（创建、读取、更新、删除）
   - 模板列表（分页、搜索）
   - Jinja2语法验证

7. **报告生成 API**
   - 异步报告生成
   - 报告详情查询
   - Markdown文件下载

8. **系统配置 API**
   - AI配置管理（OpenAI API Key）
   - 配置状态查询

9. **数据库层**
   - SQLAlchemy ORM模型
   - 5个核心数据表
   - SQLite/PostgreSQL支持

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

### 2. 启动API服务器

```bash
# 开发模式（自动重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### 3. 运行测试

```bash
# 运行所有测试（核心组件 + API）
pytest tests/ -v

# 只运行API测试
pytest tests/test_api_*.py -v

# 运行集成测试并查看输出
pytest tests/test_integration.py -v -s
```

### 3. 测试结果

✅ **40个测试全部通过**

**核心组件测试 (21个)**:
- ✅ test_context.py (5个)
- ✅ test_executors.py (5个)
- ✅ test_renderer.py (5个)
- ✅ test_scheduler.py (4个)
- ✅ test_integration.py (2个)

**API测试 (19个)**:
- ✅ test_api_templates.py (10个)
- ✅ test_api_reports.py (4个)
- ✅ test_api_config.py (3个)
- ✅ test_api_integration.py (2个)

```bash
$ pytest tests/ -q
........................................                    [100%]
40 passed, 36 warnings in 7.81s
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

## 数据库配置

### 开发环境

默认使用SQLite（`reports.db`），无需配置。

### 测试环境

**测试使用MySQL数据库**:
- 主机: 10.10.20.10:24406
- 数据库: test_report_generator
- 详见: [测试数据库配置说明.md](./测试数据库配置说明.md)

### 生产环境

设置环境变量使用PostgreSQL或MySQL：

```bash
# PostgreSQL
export DATABASE_URL="postgresql://user:password@host:port/dbname"

# MySQL
export DATABASE_URL="mysql+pymysql://user:password@host:port/dbname"
```

## 注意事项

1. **AI功能需要API Key**: 设置环境变量 `OPENAI_API_KEY`
2. **SQL功能需要数据库**: 使用 `db_connector.register_connection()` 注册连接
3. **Schema警告**: Pydantic的 `schema` 字段名与父类冲突，但不影响功能
4. **Python版本**: 推荐使用 Python 3.11 或 3.12
5. **测试数据库**: 使用MySQL远程数据库，确保网络可达

## API 使用

详细API文档请参考: [API_使用文档.md](./API_使用文档.md)

### 快速示例

```bash
# 1. 创建模板
curl -X POST http://localhost:8000/api/templates \
  -H "Content-Type: application/json" \
  -d '{"name": "简单报告", "template_content": "# {{title}}", "metadata": {...}}'

# 2. 生成报告
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"template_id": "tpl_xxx", "inputs": {"title": "我的报告"}}'

# 3. 下载报告
curl http://localhost:8000/api/reports/{report_id}/download -o report.md
```

## 项目文档

- 📄 [README.md](./README.md) - 本文档
- 📄 [API_使用文档.md](./API_使用文档.md) - API接口文档
- 📄 [P0_实现总结.md](./P0_实现总结.md) - 核心组件实现总结
- 📄 [P0_API实现总结.md](./P0_API实现总结.md) - API实现总结
- 📄 [模块说明.md](../模块说明.md) - 系统架构设计

## 贡献与反馈

本项目为MVP阶段的P0完整实现（核心组件 + REST API）。如有问题或建议，请参考《模块说明.md》中的架构设计。

