# Project Context

## Purpose

本项目是一个**Markdown 报告自动生成平台**，旨在为用户提供可配置、可扩展的报告生成能力。

核心功能：
- 用户可上传 Jinja2 格式的报告模板
- 支持多源数据注入（用户输入、SQL查询、API调用、AI生成、图片分析等）
- 自动处理变量依赖关系并按拓扑顺序执行
- 集成 LangChain 实现 AI 结构化内容生成
- 支持模板嵌套、实时调试和进度追踪
- 生成完整的 Markdown 报告，支持预览和 Word 导出

业务价值：
- 提高报告生成效率，减少重复劳动
- 统一报告格式和质量标准
- 实现数据驱动的智能报告生成

## Tech Stack

### 前端
- **React 19.x** - UI框架，使用函数组件 + Hooks
- **TypeScript 5.9** - 类型安全
- **Vite 7.x** - 构建工具
- **Ant Design 5.27** - UI组件库
- **TanStack Query** - 服务端状态管理
- **React Router DOM 7.x** - 路由管理
- **Monaco Editor** - 代码编辑器（模板编辑）
- **Axios** - HTTP客户端
- **React Markdown** - Markdown渲染
- **Recharts** - 图表可视化

### 后端
- **Python 3.11+** - 编程语言
- **FastAPI 0.109** - Web框架
- **Uvicorn** - ASGI服务器
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL** - 生产数据库
- **psycopg2** - PostgreSQL驱动
- **Jinja2 3.1** - 模板引擎
- **LangChain 0.3** - AI编排框架
- **LangChain-OpenAI 0.2** - OpenAI集成
- **OpenAI 1.51** - GPT模型调用
- **NetworkX 3.2** - 依赖图处理（DAG）
- **HTTPX** - 异步HTTP客户端
- **PyYAML** - YAML配置解析

### 基础设施
- **PostgreSQL** - 持久化存储
- **WebSocket** - 实时进度推送
- **Pandoc** - Markdown to Word 转换

## Project Conventions

### Code Style

#### 前端规范
- **组件风格**: 函数组件 + React Hooks，禁用类组件
- **TypeScript**: 
  - 严格模式启用
  - 所有Props、State、API响应必须定义接口
  - 避免使用 `any`，优先使用联合类型或泛型
- **命名规范**:
  - 组件文件和组件名: `PascalCase`（如 `GenerateReport.tsx`）
  - 普通函数/变量: `camelCase`
  - 常量: `UPPER_SNAKE_CASE`
  - 类型/接口: `PascalCase`，接口以 `I` 开头或直接使用 `type`
- **文件组织**: 按功能模块分目录（`pages/`, `components/`, `api/`, `types/`）
- **注释**: 使用中文注释，复杂逻辑必须添加说明

#### 后端规范
- **代码风格**: 严格遵循 PEP 8
- **类型提示**: 
  - 所有函数参数和返回值必须添加类型提示
  - 使用 Pydantic 定义数据模型
- **命名规范**:
  - 类名: `PascalCase`（如 `ExecutionContext`）
  - 函数/变量: `snake_case`（如 `execute_variable`）
  - 常量: `UPPER_SNAKE_CASE`（如 `DEFAULT_TIMEOUT`）
  - 私有方法: 前缀 `_`（如 `_internal_method`）
- **异步编程**: 
  - I/O密集操作优先使用 `async/await`
  - 数据库查询使用异步Session
- **文档字符串**: 使用中文 docstring，包含参数说明和返回值
- **日志规范**: 使用结构化日志，包含上下文信息（task_id、variable_name等）

### Architecture Patterns

#### 前端架构
```
src/
├── pages/          # 页面组件（路由级别）
├── components/     # 可复用UI组件
├── api/            # API调用封装
├── types/          # TypeScript类型定义
├── utils/          # 工具函数
└── hooks/          # 自定义Hooks
```

**设计模式**:
- **组件化**: 页面组件 + 展示组件分离
- **状态管理**: TanStack Query管理服务端状态，useState管理本地UI状态
- **API层**: 统一的Axios实例，集中错误处理
- **类型安全**: 完整的类型定义，编译时检查

#### 后端架构（分层设计）
```
app/
├── api/            # FastAPI路由（API层）
│   ├── templates.py
│   ├── reports.py
│   └── ...
├── services/       # 业务逻辑层
│   ├── context.py        # 执行上下文管理
│   ├── scheduler.py      # DAG调度器
│   └── renderer.py       # 模板渲染器
├── executors/      # 变量执行器（策略层）
│   ├── user_input.py
│   ├── sql.py
│   ├── api.py
│   ├── ai.py
│   └── ...
├── connectors/     # 外部连接器
│   ├── database.py
│   └── api.py
├── models/         # SQLAlchemy ORM模型
├── schemas/        # Pydantic数据模型
└── core/           # 核心工具和异常
```

**核心设计模式**:
- **分层架构**: API → Service → Executor → Connector → Database
- **策略模式**: 8种不同的变量执行器，统一接口
- **工厂模式**: ExecutorFactory根据变量类型创建执行器
- **依赖注入**: FastAPI的Depends机制管理依赖
- **DAG调度**: 基于NetworkX的拓扑排序，解决变量依赖
- **观察者模式**: WebSocket进度回调

**关键服务**:
- **ExecutionContext**: 变量存储、依赖检查、字符串插值
- **ExecutionScheduler**: DAG构建、拓扑排序、批次执行
- **TemplateRenderer**: Jinja2安全渲染、自定义过滤器

### Testing Strategy

#### 后端测试（已实施）
- **测试框架**: Pytest + pytest-asyncio + pytest-cov
- **测试层次**:
  - **单元测试**: 各个执行器、服务组件的独立测试
  - **集成测试**: 完整报告生成流程测试
  - **API测试**: FastAPI TestClient端到端测试
- **测试数据**: 独立的测试数据库 `test_p1.db`
- **配置文件**: `pytest.ini`
- **覆盖率**: 使用pytest-cov生成覆盖率报告

测试命令:
```bash
cd backend
pytest tests/                    # 运行所有测试
pytest tests/test_context.py     # 运行单个测试文件
pytest --cov=app --cov-report=html  # 生成覆盖率报告
```

#### 前端测试（建议）
- **当前状态**: 主要依赖手动测试和类型检查
- **建议工具**: Vitest + React Testing Library + MSW (Mock Service Worker)

### Git Workflow

#### 分支策略
- **主分支**: `main` 或 `master` - 稳定代码
- **功能分支**: 从主分支创建，完成后合并
- **命名规范**: `feature/功能名`、`fix/问题描述`、`refactor/重构内容`

#### 提交规范（建议遵循 Conventional Commits）
- `feat: 新功能描述` - 新功能
- `fix: 修复问题描述` - Bug修复
- `refactor: 重构说明` - 代码重构
- `docs: 文档更新` - 文档变更
- `test: 测试相关` - 测试添加或修改
- `chore: 构建/工具变更` - 构建工具、依赖更新

#### Git忽略规则
- Python编译文件: `__pycache__/`, `*.pyc`
- 虚拟环境: `venv/`, `.venv`, `env/`
- 环境配置: `.env`, `.env.local`
- 数据库文件: `*.db`, `*.sqlite`, `*.sqlite3`
- 日志文件: `*.log`, `logs/`
- IDE配置: `.vscode/`, `.idea/`, `.DS_Store`
- 测试输出: `.pytest_cache/`, `.coverage`, `htmlcov/`
- 构建产物: `dist/`, `build/`, `*.egg-info/`

## Domain Context

### 核心概念

#### 模板 (Template)
- Jinja2格式的报告模板文件（`.jinja2` 或 `.md.j2`）
- 包含变量占位符：`{{variable_name}}`
- 支持Jinja2语法：循环、条件、过滤器等
- 可嵌套引用其他模板

#### 变量 (Variable)
模板中需要注入的数据，每个变量有完整的元数据配置（YAML格式），包括：
- `type`: 数据类型（string, number, boolean, array, object）
- `source`: 数据来源（8种类型，见下方）
- `required`: 是否必需
- `default`: 默认值
- `dependencies`: 依赖的其他变量
- `schema`: 数据结构定义（用于验证）

#### 8种变量数据源
1. **user_input** - 用户表单输入
   - 动态生成表单控件
   - 支持多种输入类型（文本、数字、日期、下拉等）

2. **sql** - 数据库查询
   - 支持参数化查询
   - 多种结果模式（单行、多行、单值、单列）
   - 连接池管理

3. **api** - HTTP API调用
   - 支持GET/POST/PUT/DELETE
   - 自动重试和超时控制
   - 响应数据映射（JMESPath）
   - 类型保持（纯变量引用保持原始类型）

4. **ai_generation** - LLM生成内容
   - LangChain集成
   - 结构化输出（JSON Schema验证）
   - 自定义Prompt模板
   - 支持多轮对话和重试

5. **system** - 系统变量
   - 时间戳（`current_time`, `current_date`）
   - UUID生成
   - 环境变量

6. **constant** - 常量值
   - 直接在元数据中定义
   - 枚举类型支持

7. **image** - 图片上传
   - 用户上传图片文件
   - 返回图片路径或Base64

8. **vision_ai** - 图片AI分析
   - 使用多模态模型分析图片
   - 提取图片中的信息
   - 结构化输出

#### 变量依赖图 (Variable DAG)
- 基于 `dependencies` 字段构建有向无环图
- 使用 NetworkX 进行拓扑排序
- 按依赖层级批次执行变量
- 检测循环依赖并报错

#### 执行上下文 (ExecutionContext)
运行时环境，管理：
- 已解析变量的存储
- 变量值的获取和设置
- 字符串插值（`{{var}}` → 实际值）
- 上下文快照（用于调试）

#### 报告任务 (Report Task)
- 异步执行的报告生成任务
- 状态：pending → running → completed/failed
- WebSocket实时推送进度
- 支持任务查询和历史记录

### 业务流程

#### 报告生成流程
1. **模板选择**: 用户从模板列表选择
2. **元数据解析**: 加载模板的变量配置（YAML）
3. **表单生成**: 根据 `user_input` 类型变量动态生成表单
4. **用户填写**: 用户输入必需的参数
5. **DAG构建**: 解析变量依赖关系，构建执行图
6. **变量执行**: 按拓扑顺序执行
   - 批次1: 无依赖的变量（并行执行）
   - 批次2: 依赖批次1的变量
   - ...依此类推
7. **AI生成**: LangChain调用LLM生成结构化内容
8. **模板渲染**: Jinja2渲染最终报告
9. **结果输出**: Markdown预览、下载、Word导出

#### 嵌套模板流程
- 主模板可通过 `{% include 'sub_template.jinja2' %}` 引用子模板
- 子模板有独立的变量作用域
- 支持多层嵌套
- 调试模式可查看每层执行日志

## Important Constraints

### 技术约束
- **Python版本**: 必须 ≥ 3.11（LangChain兼容性要求）
- **数据库**: 
  - 生产环境: PostgreSQL
  - 开发环境: PostgreSQL
  - 测试环境: SQLite (单元测试) / PostgreSQL (集成测试)
  - 使用SQLAlchemy ORM，支持多种数据库
- **AI模型**: 
  - 依赖 OpenAI API
  - 必须配置 `OPENAI_API_KEY` 环境变量
  - 支持自定义 `OPENAI_API_BASE`（兼容第三方接口）
- **模板安全**: 
  - 使用 `Jinja2.SandboxedEnvironment`
  - 禁止执行危险操作（`__import__`, `getattr`, `eval`）
  - 限制访问私有属性

### 性能约束
- **SQL查询超时**: 默认30秒，可在变量元数据中配置
- **API调用超时**: 默认10秒，支持重试机制
- **AI生成超时**: 由LangChain配置控制
- **并发限制**: 
  - 同一批次的变量可并行执行
  - AI调用建议控制并发数（避免速率限制）
- **实时通信**: WebSocket推送执行进度，前端实时显示

### 安全约束
- **环境变量**: 敏感信息（API密钥、数据库密码）必须通过 `.env` 配置
- **CORS**: 
  - 开发环境允许所有来源
  - 生产环境必须限制 `allow_origins`
- **SQL注入防护**: 使用参数化查询，禁止字符串拼接
- **模板注入防护**: SandboxedEnvironment + 白名单过滤器
- **文件上传**: 
  - 限制文件类型（模板、图片）
  - 限制文件大小
  - 存储路径隔离

### 数据约束
- **模板文件**: 
  - 格式: `.jinja2` 或 `.md.j2`
  - 编码: UTF-8
  - 必须配套YAML元数据文件
- **变量元数据**: 
  - 格式: YAML
  - 必须包含必填字段（type, source, required）
  - schema 必须符合 JSON Schema 规范
- **AI输出**: 
  - 必须符合预定义的 JSON Schema
  - 解析失败时使用 default 值或重试

## External Dependencies

### AI服务
- **OpenAI API**: 
  - 模型: GPT-3.5/GPT-4/GPT-4-Vision
  - 通过 LangChain 调用
  - 环境变量: `OPENAI_API_KEY`, `OPENAI_API_BASE`
  - 计费: 按Token使用量计费
- **LangSmith** (可选): 
  - LangChain调用链路追踪
  - 调试和性能监控

### 数据库
- **PostgreSQL**: 
  - 版本: 12+ (推荐 17.x)
  - 驱动: psycopg2
  - 连接池: SQLAlchemy
  - 配置: 通过环境变量或配置文件
  - 默认连接: `postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent`

### 文档转换
- **Pandoc**: 
  - 用途: Markdown → Word (.docx)
  - 必须系统级安装
  - 安装指南: 参见 `安装pandoc指南.md`

### HTTP API
- **第三方API**: 
  - 系统支持调用任意HTTP API作为变量数据源
  - 支持自定义请求头、参数、重试策略
  - 常见用途: 天气、股票、地理位置等数据

### 监控和日志
- **应用日志**: 
  - 后端: Python logging，输出到 `logs/app.log`
  - 前端: Console日志
- **LangSmith** (可选): LangChain执行追踪

### 开发工具
- **包管理**: 
  - 前端: npm/pnpm
  - 后端: pip + requirements.txt
- **代码检查**: 
  - 前端: ESLint + TypeScript
  - 后端: 遵循PEP 8（建议集成 flake8 或 ruff）

## Special Notes

### OpenSpec集成
本项目使用 **OpenSpec** 进行变更管理和规格文档维护：
- 位置: `openspec/` 目录
- 用途: 
  - 功能提案管理 (`changes/`)
  - 能力规格文档 (`specs/`)
  - 变更历史归档 (`changes/archive/`)
- 工作流: 
  - 创建变更提案 → 实施开发 → 归档变更
  - 详见 `openspec/AGENTS.md`

### 文档管理
项目包含大量中文技术文档，位于根目录和backend目录：
- 功能说明文档（如 `报告模板编写规范指南.md`）
- 修复总结（如 `API响应schema修复说明.md`）
- 实施报告（如 `P1功能开发完成总结.md`）
- 快速开始指南（如 `快速开始.md`, `P1.0_快速开始.md`）

建议：定期整理文档，归档过时内容，保持文档目录清晰。

### 项目阶段
- **P0**: 核心组件和基础API（已完成）
- **P1.0**: 模板嵌套、调试功能（已完成）
- **P1.1-P1.3**: 图片支持、Vision AI、Word导出（已完成）
- 后续迭代: 性能优化、多租户、权限管理等
