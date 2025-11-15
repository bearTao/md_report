# 开发者指南:添加新的执行策略

## 概述

本指南面向需要扩展报告修改代理系统功能的开发者,详细说明如何添加新的执行策略(Execution Strategy)来支持新的修改操作类型。

## 目录

1. [架构概览](#1-架构概览)
2. [策略模式](#2-策略模式)
3. [添加新策略的步骤](#3-添加新策略的步骤)
4. [实战示例](#4-实战示例)
5. [测试指南](#5-测试指南)
6. [最佳实践](#6-最佳实践)

---

## 1. 架构概览

### 1.1 执行策略在系统中的位置

```
用户请求 (自然语言)
    ↓
IntentParser (解析意图)
    ↓
OperationPlanner (规划操作步骤)
    ↓
OperationExecutor (选择并执行策略)
    ↓
ExecutionStrategy ← 您将在这里添加新策略
    ├─ ParameterUpdateStrategy
    ├─ AIRefinementStrategy
    ├─ TemplateModificationStrategy
    └─ YourNewStrategy ← 新策略
```

### 1.2 策略的职责

每个执行策略负责:
1. **接收**: 操作步骤(OperationStep)和当前状态(ConversationMemory)
2. **执行**: 具体的修改操作
3. **更新**: 内存中的报告状态
4. **返回**: 操作结果(Operation)

---

## 2. 策略模式

### 2.1 基类接口

所有策略都继承自`ExecutionStrategy`基类:

```python
from abc import ABC, abstractmethod
from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    ConversationMemory
)

class ExecutionStrategy(ABC):
    """执行策略基类"""
    
    @abstractmethod
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行操作步骤
        
        Args:
            step: 操作步骤(包含操作类型和参数)
            memory: 对话记忆(包含当前报告状态)
        
        Returns:
            Operation: 执行结果
        """
        pass
```

### 2.2 辅助方法

基类提供了一个辅助方法用于创建标准的Operation对象:

```python
def _create_operation_result(
    self,
    operation_type: str,
    details: Any,
    success: bool = True,
    error_message: str = None,
    duration_ms: int = None,
    cost_usd: float = None
) -> Operation:
    """创建操作结果对象"""
    return Operation(
        operation_type=operation_type,
        details=details,
        success=success,
        error_message=error_message,
        duration_ms=duration_ms,
        cost_usd=cost_usd
    )
```

---

## 3. 添加新策略的步骤

### 步骤1: 定义新的操作类型

在`app/schemas/modification_schemas.py`中添加新的枚举值:

```python
class IntentType(str, Enum):
    """用户意图类型枚举"""
    UPDATE_PARAMETER = "update_parameter"
    REFINE_AI_CONTENT = "refine_ai_content"
    ADD_SECTION = "add_section"
    # 添加新的意图类型
    YOUR_NEW_INTENT = "your_new_intent"  # ← 新增

class OperationType(str, Enum):
    """操作类型枚举"""
    UPDATE_PARAMETER = "update_parameter"
    REFINE_AI_CONTENT = "refine_ai_content"
    ADD_SECTION = "add_section"
    # 添加新的操作类型
    YOUR_NEW_OPERATION = "your_new_operation"  # ← 新增
```

### 步骤2: 定义操作详情模型

为新操作定义详情模型:

```python
class YourNewOperationDetails(BaseModel):
    """
    新操作的详情模型
    
    Attributes:
        field1: 字段1说明
        field2: 字段2说明
    """
    field1: str = Field(..., description="字段1")
    field2: Optional[int] = Field(None, description="字段2")
    # 添加您需要的字段
```

更新`Operation`模型的`details`字段类型:

```python
class Operation(BaseModel):
    operation_type: OperationType
    details: Union[
        ParameterUpdateDetails,
        AIRefinementDetails,
        TemplateModificationDetails,
        YourNewOperationDetails,  # ← 添加新类型
    ]
    # ...其他字段
```

### 步骤3: 创建策略实现类

在`app/services/agent/strategies/`目录下创建新文件:

```python
# app/services/agent/strategies/your_new_strategy.py

"""
您的新策略

本模块实现XXX操作的具体执行逻辑。
"""
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.services.agent.strategies.base import ExecutionStrategy
from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    OperationType,
    YourNewOperationDetails,
    ConversationMemory
)

logger = logging.getLogger(__name__)


class YourNewStrategy(ExecutionStrategy):
    """
    新操作执行策略
    
    负责执行XXX操作,包括:
    1. 职责1
    2. 职责2
    3. 职责3
    
    Attributes:
        db: 数据库会话
    """
    
    def __init__(self, db: Session):
        """
        初始化策略
        
        Args:
            db: 数据库会话
        """
        self.db = db
        # 初始化其他依赖
    
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行新操作
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Returns:
            Operation: 执行结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 验证输入
            self._validate_step(step, memory)
            
            # 2. 执行核心逻辑
            result = await self._do_your_operation(step, memory)
            
            # 3. 更新内存状态
            self._update_memory_state(memory, result)
            
            # 4. 计算执行时长
            duration_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            
            # 5. 创建详情对象
            details = YourNewOperationDetails(
                field1=result["field1"],
                field2=result.get("field2")
            )
            
            # 6. 返回成功结果
            return self._create_operation_result(
                operation_type=OperationType.YOUR_NEW_OPERATION,
                details=details,
                success=True,
                duration_ms=duration_ms,
                cost_usd=result.get("cost", 0.0)
            )
            
        except Exception as e:
            logger.error(f"执行新操作失败: {str(e)}", exc_info=True)
            
            # 返回失败结果
            duration_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            
            details = YourNewOperationDetails(
                field1="",
                field2=None
            )
            
            return self._create_operation_result(
                operation_type=OperationType.YOUR_NEW_OPERATION,
                details=details,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms
            )
    
    def _validate_step(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> None:
        """
        验证操作步骤
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Raises:
            ValueError: 如果验证失败
        """
        # 添加您的验证逻辑
        if "required_param" not in step.parameters:
            raise ValueError("缺少必要参数: required_param")
    
    async def _do_your_operation(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Dict[str, Any]:
        """
        执行核心操作逻辑
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Returns:
            Dict: 操作结果
        """
        # 实现您的核心逻辑
        result = {
            "field1": "some_value",
            "field2": 123,
            "cost": 0.05
        }
        
        return result
    
    def _update_memory_state(
        self,
        memory: ConversationMemory,
        result: Dict[str, Any]
    ) -> None:
        """
        更新内存中的报告状态
        
        Args:
            memory: 对话记忆
            result: 操作结果
        """
        # 更新变量、模板内容等
        pass
```

### 步骤4: 注册策略到OperationExecutor

在`app/services/agent/operation_executor.py`中注册新策略:

```python
class OperationExecutor:
    def __init__(self, db: Session):
        self.db = db
        # 注册所有策略
        self.strategies = {
            OperationType.UPDATE_PARAMETER: ParameterUpdateStrategy(db),
            OperationType.REFINE_AI_CONTENT: AIRefinementStrategy(db),
            OperationType.ADD_SECTION: TemplateModificationStrategy(db),
            OperationType.YOUR_NEW_OPERATION: YourNewStrategy(db),  # ← 注册新策略
        }
```

### 步骤5: 更新IntentParser

在`IntentParser`的系统提示词中添加新意图类型的说明:

```python
system_prompt = """你是一个专业的报告修改意图解析助手...

**支持的意图类型:**

1. **update_parameter** - 更新参数值
   ...

# 添加新意图类型
N. **your_new_intent** - 新操作说明
   - 用户想要XXX
   - 例如: "做XXX操作"
   - 需要识别: field1(字段1), field2(字段2)
"""
```

### 步骤6: 更新OperationPlanner

在`OperationPlanner`中添加规划逻辑:

```python
class OperationPlanner:
    def create_plan(
        self,
        intents: List[ModificationIntent],
        memory: ConversationMemory
    ) -> List[OperationStep]:
        steps = []
        step_number = 1
        
        for intent in intents:
            # ...existing cases...
            
            elif intent.intent_type == "your_new_intent":
                # 规划新操作
                new_step = self._plan_your_new_operation(
                    intent, memory, step_number
                )
                steps.append(new_step)
                step_number += 1
        
        return steps
    
    def _plan_your_new_operation(
        self,
        intent: ModificationIntent,
        memory: ConversationMemory,
        step_number: int
    ) -> OperationStep:
        """规划新操作"""
        return OperationStep(
            step_number=step_number,
            operation_type=OperationType.YOUR_NEW_OPERATION,
            description=f"执行新操作: {intent.field1}",
            parameters={
                "field1": intent.field1,
                "field2": intent.field2
            }
        )
```

---

## 4. 实战示例

### 示例: 添加数据导出策略

假设我们要添加一个"导出数据"功能,允许用户导出报告中的特定数据。

#### 步骤1: 定义类型

```python
# schemas/modification_schemas.py

class IntentType(str, Enum):
    # ...
    EXPORT_DATA = "export_data"

class OperationType(str, Enum):
    # ...
    EXPORT_DATA = "export_data"

class DataExportDetails(BaseModel):
    """数据导出详情"""
    variable_name: str = Field(..., description="要导出的变量名")
    export_format: str = Field("csv", description="导出格式(csv/excel/json)")
    file_path: str = Field(..., description="导出文件路径")
    row_count: int = Field(0, description="导出行数")
```

#### 步骤2: 实现策略

```python
# services/agent/strategies/data_export.py

import pandas as pd
from pathlib import Path

class DataExportStrategy(ExecutionStrategy):
    """数据导出策略"""
    
    def __init__(self, db: Session, export_dir: str = "./exports"):
        self.db = db
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
    
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        start_time = datetime.now()
        
        try:
            # 获取参数
            var_name = step.parameters.get("variable_name")
            export_format = step.parameters.get("export_format", "csv")
            
            # 验证变量存在
            if var_name not in memory.report_state.variables:
                raise ValueError(f"变量不存在: {var_name}")
            
            var_info = memory.report_state.variables[var_name]
            
            # 获取数据
            data = var_info.value
            if not isinstance(data, (list, dict, pd.DataFrame)):
                raise ValueError(f"变量 {var_name} 不是可导出的数据类型")
            
            # 转换为DataFrame
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{var_name}_{timestamp}.{export_format}"
            file_path = self.export_dir / filename
            
            # 导出
            if export_format == "csv":
                df.to_csv(file_path, index=False, encoding="utf-8-sig")
            elif export_format == "excel":
                df.to_excel(file_path, index=False)
            elif export_format == "json":
                df.to_json(file_path, orient="records", force_ascii=False)
            else:
                raise ValueError(f"不支持的导出格式: {export_format}")
            
            logger.info(f"数据已导出: {file_path}")
            
            # 创建详情
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            details = DataExportDetails(
                variable_name=var_name,
                export_format=export_format,
                file_path=str(file_path),
                row_count=len(df)
            )
            
            return self._create_operation_result(
                operation_type=OperationType.EXPORT_DATA,
                details=details,
                success=True,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"数据导出失败: {str(e)}", exc_info=True)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            details = DataExportDetails(
                variable_name=step.parameters.get("variable_name", ""),
                export_format=step.parameters.get("export_format", "csv"),
                file_path="",
                row_count=0
            )
            
            return self._create_operation_result(
                operation_type=OperationType.EXPORT_DATA,
                details=details,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms
            )
```

#### 步骤3: 注册和集成

```python
# operation_executor.py
from app.services.agent.strategies.data_export import DataExportStrategy

class OperationExecutor:
    def __init__(self, db: Session):
        self.db = db
        self.strategies = {
            # ...
            OperationType.EXPORT_DATA: DataExportStrategy(db),
        }
```

```python
# intent_parser.py - 更新提示词
"""
N. **export_data** - 导出数据
   - 用户想要导出某个变量的数据
   - 例如: "导出data_query的数据", "把分析结果导出为Excel"
   - 需要识别: variable_name(变量名), export_format(导出格式,默认csv)
"""
```

```python
# operation_planner.py
def create_plan(self, intents, memory):
    # ...
    elif intent.intent_type == "export_data":
        step = OperationStep(
            step_number=step_number,
            operation_type=OperationType.EXPORT_DATA,
            description=f"导出数据: {intent.variable_name}",
            parameters={
                "variable_name": intent.variable_name,
                "export_format": intent.export_format or "csv"
            }
        )
        steps.append(step)
        step_number += 1
```

---

## 5. 测试指南

### 5.1 单元测试

为新策略创建单元测试:

```python
# tests/agent/test_data_export_strategy.py

import pytest
from app.services.agent.strategies.data_export import DataExportStrategy

@pytest.mark.asyncio
async def test_export_csv(db_session, sample_memory):
    """测试CSV导出"""
    # 准备测试数据
    sample_memory.report_state.variables["test_data"] = VariableInfo(
        name="test_data",
        value=[{"id": 1, "name": "测试"}],
        source="sql"
    )
    
    strategy = DataExportStrategy(db=db_session)
    
    step = OperationStep(
        step_number=1,
        operation_type=OperationType.EXPORT_DATA,
        description="导出测试数据",
        parameters={
            "variable_name": "test_data",
            "export_format": "csv"
        }
    )
    
    operation = await strategy.execute(step=step, memory=sample_memory)
    
    assert operation.success is True
    assert operation.details.row_count == 1
    assert operation.details.file_path.endswith(".csv")
    
    # 验证文件存在
    import os
    assert os.path.exists(operation.details.file_path)
```

### 5.2 集成测试

测试完整流程:

```python
@pytest.mark.asyncio
async def test_export_data_end_to_end(client, sample_report):
    """测试完整的数据导出流程"""
    response = client.post(
        f"/api/reports/{sample_report.id}/modify",
        json={
            "report_id": sample_report.id,
            "user_request": "导出data_query的数据为Excel"
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "导出" in result["explanation"]
```

---

## 6. 最佳实践

### 6.1 设计原则

1. **单一职责**: 每个策略只负责一种操作类型
2. **错误处理**: 捕获所有异常,返回失败的Operation而不是抛出异常
3. **日志记录**: 记录关键步骤和错误信息
4. **性能监控**: 记录执行时长和成本

### 6.2 代码规范

1. **类型提示**: 所有函数都应有完整的类型提示
2. **文档字符串**: 使用中文docstring,包含参数和返回值说明
3. **命名约定**: 使用清晰的变量和方法名
4. **错误消息**: 提供清晰的中文错误消息

### 6.3 性能考虑

1. **异步操作**: 使用async/await处理I/O操作
2. **批量处理**: 如可能,批量处理多个操作
3. **缓存**: 缓存重复计算的结果
4. **超时控制**: 为长时间操作设置超时

### 6.4 安全性

1. **输入验证**: 验证所有用户输入
2. **权限检查**: 检查操作权限
3. **SQL注入**: 使用参数化查询
4. **路径遍历**: 验证文件路径

### 6.5 可维护性

1. **模块化**: 将复杂逻辑拆分为小方法
2. **配置管理**: 将配置参数外部化
3. **版本控制**: 记录策略的版本信息
4. **向后兼容**: 保持API的向后兼容性

---

## 7. 常见问题

### Q1: 如何访问数据库?

**A**: 通过构造函数注入的`self.db`访问:

```python
def __init__(self, db: Session):
    self.db = db

# 使用
report = self.db.query(Report).filter(Report.id == report_id).first()
```

### Q2: 如何调用LLM?

**A**: 使用LangChain集成:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.1,
    api_key=os.getenv("OPENAI_API_KEY")
)

response = await llm.ainvoke("your prompt")
```

### Q3: 如何更新报告状态?

**A**: 直接修改memory对象:

```python
# 更新变量值
memory.report_state.variables["var_name"].value = new_value

# 更新模板内容
memory.report_state.template_content = new_template

# 更新Markdown内容
memory.report_state.markdown_content = new_markdown
```

### Q4: 如何记录成本?

**A**: 在Operation对象中设置cost_usd:

```python
return self._create_operation_result(
    operation_type=OperationType.YOUR_NEW_OPERATION,
    details=details,
    success=True,
    cost_usd=0.05  # LLM调用成本
)
```

### Q5: 如何处理长时间操作?

**A**: 使用WebSocket发送进度通知:

```python
from app.services.websocket import ConnectionManager

manager = ConnectionManager()

# 发送进度
await manager.send_progress(
    session_id=memory.session_id,
    message="正在执行操作...",
    progress=0.5
)
```

---

## 8. 资源和参考

### 相关文档
- [API文档](./API_REPORT_MODIFICATION.md)
- [用户指南](./USER_GUIDE_REPORT_MODIFICATION.md)
- [架构文档](./ARCHITECTURE.md)

### 代码示例
- [ParameterUpdateStrategy](../app/services/agent/strategies/parameter_update.py)
- [AIRefinementStrategy](../app/services/agent/strategies/ai_refinement.py)
- [TemplateModificationStrategy](../app/services/agent/strategies/template_modification.py)

### 外部资源
- [LangChain文档](https://python.langchain.com/)
- [Pydantic文档](https://docs.pydantic.dev/)
- [FastAPI文档](https://fastapi.tiangolo.com/)

---

## 9. 检查清单

在提交新策略之前,请确认:

- [ ] 已添加新的枚举类型(IntentType, OperationType)
- [ ] 已定义详情模型(Details)
- [ ] 已实现策略类(继承自ExecutionStrategy)
- [ ] 已注册到OperationExecutor
- [ ] 已更新IntentParser的提示词
- [ ] 已更新OperationPlanner的规划逻辑
- [ ] 已编写单元测试(覆盖率>80%)
- [ ] 已编写集成测试
- [ ] 已添加中文docstring
- [ ] 已添加错误处理
- [ ] 已记录执行时长
- [ ] 已记录LLM成本(如适用)
- [ ] 已测试所有边界情况
- [ ] 已更新文档

---

**祝开发顺利!** 🚀

如有问题,欢迎在Issue中讨论或联系维护团队。

