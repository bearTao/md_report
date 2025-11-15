# 报告修改代理 - 架构文档

## 文档概述

本文档详细描述了报告修改代理系统的技术架构、设计决策和实现细节。

**目标读者**: 系统架构师、高级开发者、技术决策者

## 目录

1. [系统概述](#1-系统概述)
2. [架构设计](#2-架构设计)
3. [核心组件](#3-核心组件)
4. [数据模型](#4-数据模型)
5. [执行流程](#5-执行流程)
6. [设计决策](#6-设计决策)
7. [性能优化](#7-性能优化)
8. [安全性](#8-安全性)
9. [可扩展性](#9-可扩展性)
10. [未来规划](#10-未来规划)

---

## 1. 系统概述

### 1.1 功能定位

报告修改代理系统是一个基于AI的报告修改服务,允许用户通过自然语言对话的方式修改已生成的报告,而无需重新生成整份报告。

### 1.2 核心能力

- **自然语言理解**: 解析用户的中文修改请求
- **智能规划**: 自动分析依赖关系并规划执行步骤
- **多类型操作**: 支持参数更新、AI内容优化、模板结构修改
- **上下文记忆**: 支持多轮对话和引用解析
- **状态管理**: 版本化的报告状态管理

### 1.3 技术栈

- **Web框架**: FastAPI
- **ORM**: SQLAlchemy
- **AI框架**: LangChain + OpenAI GPT-4
- **数据验证**: Pydantic
- **数据库**: PostgreSQL
- **模板引擎**: Jinja2
- **异步支持**: asyncio
- **WebSocket**: FastAPI WebSocket

---

## 2. 架构设计

### 2.1 分层架构

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│      (REST API + WebSocket)             │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│         Application Layer               │
│    (ReportModificationAgent)            │
│  ┌──────────────────────────────────┐   │
│  │  IntentParser                    │   │
│  │  OperationPlanner                │   │
│  │  OperationExecutor               │   │
│  │  ExplanationGenerator            │   │
│  │  MemoryManager                   │   │
│  └──────────────────────────────────┘   │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│           Service Layer                 │
│  ┌──────────────────────────────────┐   │
│  │  ExecutionScheduler              │   │
│  │  TemplateRenderer                │   │
│  │  VariableExecutors (8 types)    │   │
│  └──────────────────────────────────┘   │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│           Data Layer                    │
│  ┌──────────────────────────────────┐   │
│  │  SQLAlchemy ORM                  │   │
│  │  PostgreSQL Database             │   │
│  │  LLM API (OpenAI)                │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 2.2 组件交互

```
用户请求
   │
   ▼
[API Endpoint] ───┐
   │              │
   ▼              ▼
[ReportModificationAgent]
   │
   ├──► [IntentParser] ──► LLM (GPT-4)
   │        │
   │        ▼
   ├──► [OperationPlanner]
   │        │
   │        ▼
   ├──► [OperationExecutor]
   │        │
   │        ├──► [ParameterUpdateStrategy]
   │        │        │
   │        │        ▼
   │        │    [ExecutionScheduler] ──► [VariableExecutors]
   │        │
   │        ├──► [AIRefinementStrategy] ──► LLM (GPT-4)
   │        │
   │        └──► [TemplateModificationStrategy] ──► LLM (GPT-4)
   │
   ├──► [ExplanationGenerator] ──► LLM (GPT-4)
   │
   └──► [MemoryManager] ──► Database
         │
         ▼
    [Database]
         │
         └──► [ConversationSessions]
         │    [ConversationTurns]
         │    [ReportStates]
         │    [ModificationHistory]
         │
         ▼
    返回结果给用户
```

### 2.3 Agent模式

采用Agent设计模式,核心思想是:
- **感知(Perceive)**: IntentParser解析用户意图
- **规划(Plan)**: OperationPlanner制定执行计划
- **执行(Execute)**: OperationExecutor执行计划
- **学习(Learn)**: MemoryManager管理上下文和历史
- **反馈(Feedback)**: ExplanationGenerator生成用户友好的响应

---

## 3. 核心组件

### 3.1 ReportModificationAgent

**职责**: 修改流程的总编排者

**主要方法**:
```python
async def modify_report(
    self,
    report_id: str,
    user_request: str,
    session_id: Optional[str] = None
) -> ModificationResult
```

**流程**:
1. 获取或创建会话记忆
2. 解析用户意图
3. 规划操作步骤
4. 执行操作
5. 生成解释
6. 保存状态
7. 返回结果

### 3.2 IntentParser

**职责**: 将自然语言请求解析为结构化意图

**技术实现**:
- 使用LangChain的Pydantic输出解析器
- 基于GPT-4的提示词工程
- 支持多意图识别
- 支持引用解析

**输入**: 用户请求 + 对话上下文

**输出**: `List[ModificationIntent]`

**关键特性**:
- 中文理解
- 代词引用解析
- 相对值处理
- 模糊匹配

### 3.3 OperationPlanner

**职责**: 将意图转换为具体的执行步骤

**核心算法**:
- 依赖关系分析(DAG遍历)
- 执行顺序规划
- 参数验证

**输入**: `List[ModificationIntent]` + `ConversationMemory`

**输出**: `List[OperationStep]`

**关键特性**:
- 自动检测依赖变量
- 避免循环依赖
- 优化执行顺序

### 3.4 OperationExecutor

**职责**: 执行操作步骤,使用策略模式

**架构模式**: 策略模式

**支持的策略**:
1. **ParameterUpdateStrategy**: 参数更新
2. **AIRefinementStrategy**: AI内容优化
3. **TemplateModificationStrategy**: 模板结构修改

**扩展性**: 可轻松添加新策略

### 3.5 MemoryManager

**职责**: 管理对话会话和报告状态

**核心功能**:
- 会话生命周期管理
- 状态版本化
- 对话历史存储
- 上下文总结(长对话)

**存储策略**:
- 数据库持久化
- 内存缓存优化

### 3.6 ExplanationGenerator

**职责**: 生成用户友好的响应说明

**技术实现**:
- 基于LLM的自然语言生成
- 模板化输出格式
- 中文本地化

---

## 4. 数据模型

### 4.1 数据库Schema

```sql
-- 对话会话表
CREATE TABLE conversation_sessions (
    id VARCHAR(50) PRIMARY KEY,
    report_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    context_summary TEXT,
    last_activity_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 对话轮次表
CREATE TABLE conversation_turns (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    turn_number INTEGER NOT NULL,
    user_request TEXT NOT NULL,
    parsed_intents JSONB NOT NULL,
    operations JSONB NOT NULL,
    system_response TEXT NOT NULL,
    report_version INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(id)
);

-- 报告状态表
CREATE TABLE report_states (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    template_id VARCHAR(50) NOT NULL,
    template_content TEXT,
    template_metadata JSONB,
    variables_state JSONB NOT NULL,
    markdown_content TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(id),
    UNIQUE(session_id, version)
);

-- 修改历史表
CREATE TABLE report_modification_history (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    turn_number INTEGER NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    operation_details JSONB NOT NULL,
    from_version INTEGER NOT NULL,
    to_version INTEGER NOT NULL,
    duration_ms INTEGER,
    cost_usd NUMERIC(10,4),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(id)
);

-- 索引
CREATE INDEX idx_conversation_sessions_report_id ON conversation_sessions(report_id);
CREATE INDEX idx_conversation_turns_session_id ON conversation_turns(session_id);
CREATE INDEX idx_report_states_session_id ON report_states(session_id);
CREATE INDEX idx_report_modification_history_report_id ON report_modification_history(report_id);
```

### 4.2 核心Pydantic模型

#### ModificationIntent
```python
class ModificationIntent(BaseModel):
    intent_type: IntentType
    target_variable: Optional[str]
    target_section: Optional[str]
    new_value: Optional[Any]
    refinement_instruction: Optional[str]
    section_description: Optional[str]
    confidence: float = 1.0
```

#### ReportState
```python
class ReportState(BaseModel):
    report_id: str
    version: int
    template_id: str
    template_content: Optional[str]
    template_metadata: Optional[Dict[str, Any]]
    variables: Dict[str, VariableInfo]
    markdown_content: str
```

#### ConversationMemory
```python
class ConversationMemory(BaseModel):
    session_id: str
    report_id: str
    report_state: ReportState
    conversation_history: List[ConversationTurn]
    context_summary: Optional[str]
    current_version: int
```

---

## 5. 执行流程

### 5.1 完整修改流程

```
1. 用户请求到达
   ├─ 验证报告存在
   └─ 创建/加载会话

2. 意图解析
   ├─ 构建上下文(最近N轮对话)
   ├─ 调用GPT-4解析意图
   ├─ 验证解析结果
   └─ 返回意图列表

3. 操作规划
   ├─ 遍历意图列表
   ├─ 为每个意图生成操作步骤
   │   ├─ 参数更新 → 分析依赖 → 生成多个步骤
   │   ├─ AI优化 → 单个步骤
   │   └─ 模板修改 → 单个步骤
   └─ 返回步骤列表

4. 操作执行
   ├─ 遍历步骤列表
   ├─ 选择对应策略
   ├─ 执行操作
   │   ├─ 更新内存状态
   │   ├─ 调用相关服务
   │   └─ 记录执行结果
   └─ 收集所有结果

5. 渲染报告
   ├─ 使用Jinja2渲染模板
   ├─ 生成新的Markdown内容
   └─ 更新报告状态

6. 生成解释
   ├─ 格式化操作结果
   ├─ 调用GPT-4生成说明
   └─ 生成用户友好文本

7. 保存状态
   ├─ 创建新版本
   ├─ 保存对话轮次
   ├─ 保存修改历史
   └─ 更新会话状态

8. 返回结果
   └─ 返回ModificationResult
```

### 5.2 参数更新详细流程

```
参数更新请求: "把wgid改成ZQGY0175"
   │
   ▼
1. 意图解析
   └─> ModificationIntent(
        intent_type="update_parameter",
        target_variable="wgid",
        new_value="ZQGY0175"
       )
   │
   ▼
2. 操作规划
   ├─> 步骤1: 更新wgid值
   ├─> 步骤2: 重新执行data_query (依赖wgid)
   ├─> 步骤3: 重新执行title (依赖wgid)
   └─> 步骤4: 重新执行analysis (依赖data_query)
   │
   ▼
3. 执行步骤1: ParameterUpdateStrategy
   ├─> 获取旧值: "ZQGY0001"
   ├─> 设置新值: "ZQGY0175"
   └─> 更新内存: memory.report_state.variables["wgid"].value = "ZQGY0175"
   │
   ▼
4. 执行步骤2-4: 重新执行依赖变量
   ├─> 使用ExecutionScheduler
   ├─> 调用对应的VariableExecutor
   └─> 更新变量值
   │
   ▼
5. 渲染报告
   ├─> 使用Jinja2模板
   ├─> 填充所有变量
   └─> 生成新Markdown
   │
   ▼
6. 生成解释
   └─> "已将wgid更新为ZQGY0175,并重新执行了3个依赖变量"
```

### 5.3 AI内容优化详细流程

```
AI优化请求: "让分析更详细"
   │
   ▼
1. 意图解析
   └─> ModificationIntent(
        intent_type="refine_ai_content",
        target_variable="analysis",
        refinement_instruction="让分析更详细"
       )
   │
   ▼
2. 操作规划
   └─> 步骤1: 优化analysis变量
   │
   ▼
3. 执行: AIRefinementStrategy
   ├─> 获取原始prompt
   ├─> 获取当前内容
   ├─> 构建优化prompt:
   │    "基于以下内容: [当前内容]
   │     根据要求优化: 让分析更详细
   │     生成优化后的内容"
   ├─> 调用GPT-4生成新内容
   ├─> 更新变量值
   └─> 记录内容变化(长度对比)
   │
   ▼
4. 渲染报告
   └─> 使用新的analysis值重新渲染
   │
   ▼
5. 生成解释
   └─> "已优化分析内容,从500字扩展到1200字,增加了详细的数据支撑"
```

### 5.4 添加章节详细流程

```
添加章节请求: "添加竞争对手分析章节"
   │
   ▼
1. 意图解析
   └─> ModificationIntent(
        intent_type="add_section",
        target_section="竞争对手分析",
        section_description="分析主要竞争对手"
       )
   │
   ▼
2. 操作规划
   └─> 步骤1: 添加竞争对手分析章节
   │
   ▼
3. 执行: TemplateModificationStrategy
   ├─> 分析插入位置(在"市场分析"后)
   ├─> 分析数据需求:
   │    ├─> 调用GPT-4: "需要什么数据?"
   │    └─> 生成: {"sql": "SELECT * FROM competitors", ...}
   ├─> 执行数据查询
   │    └─> 创建运行时变量: competitor_data
   ├─> 生成Jinja2模板:
   │    ├─> 调用GPT-4生成章节模板
   │    └─> "## 竞争对手分析\n\n{{ competitor_analysis }}"
   ├─> 生成AI内容变量:
   │    └─> 创建运行时变量: competitor_analysis
   ├─> 插入到模板中
   └─> 更新template_content
   │
   ▼
4. 渲染报告
   └─> 使用新模板渲染
   │
   ▼
5. 生成解释
   └─> "已添加'竞争对手分析'章节,包含市场份额对比和策略分析"
```

---

## 6. 设计决策

### 6.1 为什么使用Agent模式?

**决策**: 采用Agent设计模式(感知-规划-执行-学习)

**原因**:
1. **复杂性管理**: 将复杂的修改流程拆分为多个阶段
2. **灵活性**: 每个阶段可独立优化和替换
3. **可测试性**: 每个组件可独立测试
4. **可扩展性**: 易于添加新的意图类型和执行策略

**替代方案**:
- 直接的规则引擎 → 灵活性不足
- 端到端的大模型 → 成本高,可控性差

### 6.2 为什么使用策略模式?

**决策**: 使用策略模式实现不同类型的修改操作

**原因**:
1. **开闭原则**: 添加新策略无需修改现有代码
2. **单一职责**: 每个策略只负责一种操作
3. **代码复用**: 通过基类共享通用逻辑
4. **易于测试**: 每个策略可独立测试

### 6.3 为什么区分模板变量和运行时变量?

**决策**: 引入`VariableType.TEMPLATE`和`VariableType.RUNTIME`区分

**原因**:
1. **清晰性**: 明确哪些变量来自模板定义,哪些是临时创建的
2. **持久化**: 模板变量保存到模板中,运行时变量仅存在于当前报告
3. **版本控制**: 便于追踪变量的来源和生命周期

### 6.4 为什么使用临时模板?

**决策**: 模板修改默认生成临时模板,需手动保存才永久化

**原因**:
1. **安全性**: 避免意外修改影响其他报告
2. **灵活性**: 允许用户试验不同的结构
3. **可逆性**: 临时修改不影响原始模板
4. **用户控制**: 用户明确决定是否保存

### 6.5 为什么使用版本化状态?

**决策**: 每次修改创建新版本的报告状态

**原因**:
1. **审计**: 完整的修改历史
2. **回滚**: (未来)支持回退到历史版本
3. **对比**: 可以对比不同版本的差异
4. **并发**: 避免并发修改冲突

### 6.6 LLM使用策略

**决策**: 规则引擎 + LLM混合模式

**LLM使用场景**:
- 意图解析(必须)
- AI内容优化(必须)
- 数据需求分析(必须)
- Jinja2生成(必须)
- 解释生成(必须)

**规则引擎场景**:
- 依赖关系分析
- 操作规划
- 参数更新
- 变量重新执行

**原因**:
1. **成本控制**: 规则引擎零成本
2. **可靠性**: 规则引擎更稳定
3. **性能**: 规则引擎更快
4. **可控性**: 规则逻辑明确可控

---

## 7. 性能优化

### 7.1 LLM调用优化

**策略**:
1. **批量调用**: 尽可能合并多个LLM调用
2. **缓存**: 缓存常见的解析结果
3. **并行**: 独立的LLM调用并行执行
4. **模型选择**: 简单任务使用GPT-3.5,复杂任务使用GPT-4

**成本控制**:
- 意图解析: ~$0.01-0.02/次
- AI优化: ~$0.05-0.15/次
- 模板修改: ~$0.10-0.30/次
- 目标: 单次修改 < $0.50

### 7.2 数据库优化

**索引策略**:
```sql
-- 高频查询索引
CREATE INDEX idx_sessions_report ON conversation_sessions(report_id);
CREATE INDEX idx_sessions_status ON conversation_sessions(status);
CREATE INDEX idx_turns_session ON conversation_turns(session_id);
CREATE INDEX idx_states_session_version ON report_states(session_id, version);
```

**查询优化**:
- 使用连接查询减少往返次数
- 只查询需要的字段
- 使用分页限制结果数量

### 7.3 内存管理

**策略**:
- 限制对话历史在内存中的数量(默认10轮)
- 长对话自动生成总结
- 及时清理不活跃的会话

### 7.4 异步处理

**使用场景**:
- 所有I/O操作(数据库、LLM、API)
- 长时间的变量执行
- WebSocket消息发送

**实现**:
```python
async def modify_report(self, ...):
    # 所有耗时操作使用await
    intents = await self.intent_parser.parse(...)
    operations = await self.executor.execute_all(...)
    explanation = await self.explanation_generator.generate(...)
```

---

## 8. 安全性

### 8.1 输入验证

**验证点**:
1. 报告ID存在性验证
2. 会话ID合法性验证
3. 请求长度限制(< 2000字符)
4. SQL注入防护(使用参数化查询)
5. 模板注入防护(Jinja2沙箱)

### 8.2 权限控制

**计划实现**:
- 报告所有权验证
- 会话所有权验证
- API速率限制
- 成本配额限制

### 8.3 数据隐私

**措施**:
- 敏感数据加密存储
- 对话历史定期清理
- 遵守数据保留政策
- 审计日志记录

---

## 9. 可扩展性

### 9.1 水平扩展

**无状态设计**:
- Agent实例无状态,可水平扩展
- 状态存储在数据库中
- WebSocket连接可以分布式

**负载均衡**:
```
           Load Balancer
                │
     ┌──────────┼──────────┐
     │          │          │
  Agent1     Agent2     Agent3
     │          │          │
     └──────────┼──────────┘
                │
           Database
```

### 9.2 添加新策略

**步骤**:
1. 定义新的Intent和Operation类型
2. 创建新的Strategy类
3. 注册到OperationExecutor
4. 更新IntentParser提示词
5. 更新OperationPlanner规划逻辑

**示例**: [开发者指南](./DEVELOPER_GUIDE_STRATEGIES.md)

### 9.3 集成新的变量执行器

**已有8种执行器**:
- UserInputExecutor
- SQLExecutor
- APIExecutor
- AIGenerationExecutor
- SystemExecutor
- ConstantExecutor
- ImageExecutor
- VisionAIExecutor

**添加新执行器**: 实现`VariableExecutor`接口

### 9.4 支持新的AI模型

**当前**: OpenAI GPT-4

**扩展方案**:
```python
# 通过配置切换模型
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "gpt-4"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)
```

**支持其他模型**:
- Azure OpenAI
- 本地部署的模型(通过OpenAI兼容API)
- 其他LLM提供商(通过LangChain)

---

## 10. 未来规划

### 10.1 短期规划(3个月)

#### 功能增强
- [ ] 支持版本回滚
- [ ] 批量操作优化
- [ ] 更多的意图类型(如数据导出)
- [ ] 更丰富的引用解析

#### 性能优化
- [ ] LLM响应缓存
- [ ] 预加载常用数据
- [ ] 并行执行独立操作
- [ ] 更好的成本控制

#### 用户体验
- [ ] 实时预览
- [ ] 撤销/重做
- [ ] 版本对比
- [ ] 修改建议

### 10.2 中期规划(6个月)

#### 智能化
- [ ] 主动建议优化点
- [ ] 学习用户偏好
- [ ] 智能模板推荐
- [ ] 异常检测和自动修复

#### 协作功能
- [ ] 多人协作编辑
- [ ] 评论和批注
- [ ] 修改审批流程
- [ ] 变更通知

### 10.3 长期规划(1年+)

#### 平台化
- [ ] 插件系统
- [ ] 自定义策略
- [ ] 第三方集成
- [ ] 开发者市场

#### AI能力
- [ ] 多模态支持(图片、图表)
- [ ] 更复杂的推理
- [ ] 自主决策能力
- [ ] 持续学习

---

## 11. 监控和可观测性

### 11.1 关键指标

**性能指标**:
- 意图解析时长
- 操作执行时长
- 端到端响应时间
- LLM API延迟

**成本指标**:
- 每次修改的LLM成本
- 每个用户的累计成本
- 成本趋势

**质量指标**:
- 意图解析准确率
- 操作成功率
- 用户满意度
- 错误率

### 11.2 日志策略

**日志级别**:
- DEBUG: 详细执行流程
- INFO: 关键步骤和结果
- WARNING: 潜在问题
- ERROR: 执行失败

**结构化日志**:
```python
logger.info(
    "修改完成",
    extra={
        "report_id": report_id,
        "session_id": session_id,
        "operations_count": len(operations),
        "duration_ms": duration_ms,
        "cost_usd": total_cost
    }
)
```

### 11.3 追踪

**分布式追踪**:
- 使用trace_id关联所有日志
- 跨服务调用追踪
- 性能瓶颈识别

---

## 12. 故障恢复

### 12.1 故障场景

**LLM服务不可用**:
- 自动重试(最多3次)
- 降级策略(返回友好错误)
- 备用模型切换

**数据库故障**:
- 连接池管理
- 自动重连
- 读写分离

**长时间操作超时**:
- 设置合理超时时间
- 支持操作取消
- 部分成功处理

### 12.2 数据一致性

**事务管理**:
- 关键操作使用数据库事务
- 失败自动回滚
- 保证状态一致性

**冲突处理**:
- 版本号乐观锁
- 检测并发修改
- 提示用户重新加载

---

## 13. 技术债务和已知问题

### 13.1 已知限制

1. **不支持并发修改**: 同一报告的同时修改可能冲突
2. **无版本回滚**: 当前只能通过新修改还原
3. **LLM依赖**: 核心功能依赖外部LLM服务
4. **成本控制**: 高频使用可能产生较高成本

### 13.2 技术债务

1. **测试覆盖率**: 部分集成测试待完善
2. **文档同步**: 代码更新后文档需及时更新
3. **性能优化**: 部分查询可进一步优化
4. **错误处理**: 某些边界情况处理不够完善

---

## 14. 参考文档

### 内部文档
- [API文档](./API_REPORT_MODIFICATION.md)
- [用户指南](./USER_GUIDE_REPORT_MODIFICATION.md)
- [开发者指南](./DEVELOPER_GUIDE_STRATEGIES.md)

### 外部资源
- [LangChain文档](https://python.langchain.com/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Pydantic文档](https://docs.pydantic.dev/)
- [Jinja2文档](https://jinja.palletsprojects.com/)

---

## 15. 联系方式

**架构团队**: architecture@example.com

**问题反馈**: https://github.com/yourproject/issues

**文档更新**: 2024-01-15

---

**本文档持续更新中**

