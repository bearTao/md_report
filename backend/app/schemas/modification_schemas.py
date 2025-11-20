"""
报告修改代理的数据结构定义

本模块定义了报告修改代理系统中使用的所有Pydantic模型,包括:
- 意图解析相关模型
- 操作执行相关模型
- 报告状态管理模型
- 对话记忆管理模型
- API请求响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union, Literal
from datetime import datetime
from enum import Enum


# ============================================================================
# 枚举类型定义
# ============================================================================

class IntentType(str, Enum):
    """
    用户意图类型枚举
    
    定义了系统支持的所有修改意图类型。
    """
    # 修改类意图
    UPDATE_PARAMETER = "update_parameter"  # 更新参数值
    REFINE_AI_CONTENT = "refine_ai_content"  # 优化AI生成的内容
    ADD_SECTION = "add_section"  # 添加新章节
    MODIFY_SECTION = "modify_section"  # 修改现有章节
    REMOVE_SECTION = "remove_section"  # 删除章节
    
    # 查询和通用类意图
    QUERY = "query"  # 查询报告信息（如：输出当前报告内容、显示参数列表等）
    GENERAL_CONVERSATION = "general_conversation"  # 通用对话（如：问候、咨询、建议等）


class OperationType(str, Enum):
    """
    操作类型枚举
    
    定义了系统执行的所有操作类型。
    """
    # 修改类操作
    UPDATE_PARAMETER = "update_parameter"
    REFINE_AI_CONTENT = "refine_ai_content"
    ADD_SECTION = "add_section"
    MODIFY_SECTION = "modify_section"
    REMOVE_SECTION = "remove_section"
    
    # 查询和通用类操作
    QUERY = "query"
    GENERAL_CONVERSATION = "general_conversation"


class VariableType(str, Enum):
    """
    变量类型枚举
    
    区分模板定义的变量和运行时创建的变量。
    """
    TEMPLATE = "template"  # 模板定义的变量
    RUNTIME = "runtime"  # 运行时创建的变量


# ============================================================================
# 意图解析相关模型
# ============================================================================

class ModificationIntent(BaseModel):
    """
    修改意图模型
    
    表示从用户请求中解析出的单个修改意图。
    
    Attributes:
        intent_type: 意图类型
        target_variable: 目标变量名（如果适用）
        target_section: 目标章节名（如果适用）
        new_value: 新的值（用于参数更新）
        refinement_instruction: 优化指令（用于AI内容优化）
        section_description: 新章节描述（用于添加章节）
        query_type: 查询类型（用于QUERY意图，如：show_content, list_variables, show_parameters等）
        query_details: 查询详细信息（用于QUERY和GENERAL_CONVERSATION意图）
        conversation_context: 对话上下文（用于GENERAL_CONVERSATION意图）
        confidence: 解析置信度（0-1）
    """
    intent_type: IntentType = Field(..., description="意图类型")
    target_variable: Optional[str] = Field(None, description="目标变量名")
    target_section: Optional[str] = Field(None, description="目标章节名")
    new_value: Optional[Any] = Field(None, description="新的参数值")
    refinement_instruction: Optional[str] = Field(None, description="AI内容优化指令")
    section_description: Optional[str] = Field(None, description="新章节描述")
    query_type: Optional[str] = Field(None, description="查询类型")
    query_details: Optional[Dict[str, Any]] = Field(None, description="查询详细信息")
    conversation_context: Optional[str] = Field(None, description="对话上下文")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="解析置信度")
    
    class Config:
        use_enum_values = True


# ============================================================================
# 操作执行相关模型
# ============================================================================

class ParameterUpdateDetails(BaseModel):
    """
    参数更新操作详情
    
    Attributes:
        variable_name: 变量名
        old_value: 旧值
        new_value: 新值
        dependent_variables: 受影响的依赖变量列表
    """
    variable_name: str = Field(..., description="变量名")
    old_value: Any = Field(None, description="旧值")
    new_value: Any = Field(..., description="新值")
    dependent_variables: List[str] = Field(default_factory=list, description="依赖变量列表")


class AIRefinementDetails(BaseModel):
    """
    AI内容优化操作详情
    
    Attributes:
        variable_name: AI变量名
        instruction: 优化指令
        old_prompt: 原始提示词
        new_prompt: 新提示词
        old_content_length: 原内容长度
        new_content_length: 新内容长度
    """
    variable_name: str = Field(..., description="AI变量名")
    instruction: str = Field(..., description="优化指令")
    old_prompt: Optional[str] = Field(None, description="原始提示词")
    new_prompt: str = Field(..., description="新提示词")
    old_content_length: Optional[int] = Field(None, description="原内容长度")
    new_content_length: Optional[int] = Field(None, description="新内容长度")


class TemplateModificationDetails(BaseModel):
    """
    模板修改操作详情
    
    Attributes:
        modification_type: 修改类型（add/modify/remove）
        section_name: 章节名称
        section_content: 章节内容（Jinja2模板）
        insertion_point: 插入位置（对于add操作）
        new_variables: 新创建的变量列表
    """
    modification_type: Literal["add", "modify", "remove"] = Field(..., description="修改类型")
    section_name: str = Field(..., description="章节名称")
    section_content: Optional[str] = Field(None, description="章节Jinja2内容")
    insertion_point: Optional[str] = Field(None, description="插入位置")
    new_variables: List[str] = Field(default_factory=list, description="新创建的变量")


class QueryDetails(BaseModel):
    """
    查询操作详情
    
    Attributes:
        query_type: 查询类型（show_content, list_variables, show_parameters等）
        query_result: 查询结果
        result_format: 结果格式（text, json, markdown等）
    """
    query_type: str = Field(..., description="查询类型")
    query_result: Any = Field(..., description="查询结果")
    result_format: str = Field(default="text", description="结果格式")


class GeneralConversationDetails(BaseModel):
    """
    通用对话操作详情
    
    Attributes:
        user_message: 用户消息
        system_response: 系统响应
        conversation_type: 对话类型（greeting, question, suggestion等）
    """
    user_message: str = Field(..., description="用户消息")
    system_response: str = Field(..., description="系统响应")
    conversation_type: str = Field(default="general", description="对话类型")


class Operation(BaseModel):
    """
    操作模型
    
    表示一个待执行或已执行的操作。
    
    Attributes:
        operation_type: 操作类型
        details: 操作详情（根据类型不同而不同）
        success: 是否成功执行
        error_message: 错误信息（如果失败）
        duration_ms: 执行时长（毫秒）
        cost_usd: LLM调用成本（美元）
    """
    operation_type: OperationType = Field(..., description="操作类型")
    details: Union[
        ParameterUpdateDetails, 
        AIRefinementDetails, 
        TemplateModificationDetails,
        QueryDetails,
        GeneralConversationDetails
    ] = Field(..., description="操作详情")
    success: bool = Field(True, description="执行是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[int] = Field(None, description="执行时长（毫秒）")
    cost_usd: Optional[float] = Field(None, description="LLM成本（美元）")
    
    class Config:
        use_enum_values = True


class OperationStep(BaseModel):
    """
    操作步骤模型
    
    用于操作规划阶段,表示待执行的操作步骤。
    
    Attributes:
        step_number: 步骤编号
        operation_type: 操作类型
        description: 步骤描述
        target_variable: 目标变量名
        parameters: 执行参数
    """
    step_number: int = Field(..., description="步骤编号")
    operation_type: OperationType = Field(..., description="操作类型")
    description: str = Field(..., description="步骤描述")
    target_variable: Optional[str] = Field(None, description="目标变量")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    
    class Config:
        use_enum_values = True


# ============================================================================
# 报告状态管理相关模型
# ============================================================================

class VariableInfo(BaseModel):
    """
    变量信息模型
    
    存储单个变量的完整状态信息。
    
    Attributes:
        name: 变量名
        value: 变量值
        source: 数据源类型（user_input/sql/api/ai_generation等）
        variable_type: 变量类型（template/runtime）
        metadata: 变量元数据（包括配置、依赖关系等）
        last_updated: 最后更新时间
        generation_context: 生成上下文（用于AI变量重新生成）
    """
    name: str = Field(..., description="变量名")
    value: Any = Field(..., description="变量值")
    source: str = Field(..., description="数据源类型")
    variable_type: VariableType = Field(VariableType.TEMPLATE, description="变量类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="变量元数据")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    generation_context: Optional[Dict[str, Any]] = Field(None, description="生成上下文")
    
    class Config:
        use_enum_values = True


class ReportState(BaseModel):
    """
    报告状态模型
    
    存储报告在某个时间点的完整状态。
    
    Attributes:
        report_id: 报告ID
        version: 版本号
        template_id: 模板ID
        template_content: 模板内容（可能是临时修改的）
        template_metadata: 模板元数据
        variables: 所有变量的状态信息
        markdown_content: 渲染后的Markdown内容
        edit_mode: 编辑模式（template可修改参数 | locked静态锁定）
        variable_snapshot: 变量快照（锁定时保存的历史值）
        generated_at: 报告生成时间
        locked_at: 锁定时间
        lock_reason: 锁定原因
    """
    report_id: str = Field(..., description="报告ID")
    version: int = Field(1, description="版本号")
    template_id: str = Field(..., description="模板ID")
    template_content: Optional[str] = Field(None, description="临时模板内容")
    template_metadata: Optional[Dict[str, Any]] = Field(None, description="临时模板元数据")
    variables: Dict[str, VariableInfo] = Field(default_factory=dict, description="变量状态字典")
    markdown_content: str = Field("", description="Markdown内容")
    
    # 新增：编辑模式和锁定相关字段
    edit_mode: str = Field(default="template", description="编辑模式: template | locked")
    variable_snapshot: Optional[Dict[str, Any]] = Field(None, description="变量快照（锁定时）")
    generated_at: datetime = Field(default_factory=datetime.now, description="报告生成时间")
    locked_at: Optional[datetime] = Field(None, description="锁定时间")
    lock_reason: Optional[str] = Field(None, description="锁定原因")
    
    def is_editable(self) -> bool:
        """是否可以修改参数"""
        return self.edit_mode == "template"
    
    def lock_for_content_edit(self, reason: str = "用户删除章节"):
        """锁定报告为静态版本"""
        from loguru import logger
        
        self.edit_mode = "locked"
        self.locked_at = datetime.now()
        self.lock_reason = reason
        
        # 保存变量快照
        self.variable_snapshot = {
            name: var.value 
            for name, var in self.variables.items()
        }
        
        logger.info(f"报告已锁定: {reason}, 生成时间: {self.generated_at}")


# ============================================================================
# 对话记忆管理相关模型
# ============================================================================

class ConversationTurn(BaseModel):
    """
    对话轮次模型
    
    表示对话中的一个交互轮次。
    
    Attributes:
        turn_number: 轮次编号
        user_request: 用户请求
        parsed_intents: 解析出的意图列表
        operations: 执行的操作列表
        system_response: 系统响应
        report_version: 关联的报告版本号
        timestamp: 时间戳
    """
    turn_number: int = Field(..., description="轮次编号")
    user_request: str = Field(..., description="用户请求")
    parsed_intents: List[ModificationIntent] = Field(default_factory=list, description="解析的意图")
    operations: List[Operation] = Field(default_factory=list, description="执行的操作")
    system_response: str = Field(..., description="系统响应")
    report_version: int = Field(..., description="报告版本号")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ConversationMemory(BaseModel):
    """
    对话记忆模型
    
    存储整个对话会话的完整状态。
    
    Attributes:
        session_id: 会话ID
        report_id: 报告ID
        report_state: 当前报告状态
        conversation_history: 对话历史（最近的N轮）
        context_summary: 上下文总结（长对话时使用）
        current_version: 当前版本号
    """
    session_id: str = Field(..., description="会话ID")
    report_id: str = Field(..., description="报告ID")
    report_state: ReportState = Field(..., description="报告状态")
    conversation_history: List[ConversationTurn] = Field(default_factory=list, description="对话历史")
    context_summary: Optional[str] = Field(None, description="上下文总结")
    current_version: int = Field(1, description="当前版本号")


# ============================================================================
# 修改结果模型
# ============================================================================

class ModificationMetadata(BaseModel):
    """
    修改元数据模型
    
    包含修改过程的统计和元数据信息。
    
    Attributes:
        total_duration_ms: 总执行时长（毫秒）
        total_cost_usd: 总LLM成本（美元）
        operations_count: 操作数量
        llm_calls_count: LLM调用次数
        from_version: 修改前版本号
        to_version: 修改后版本号
    """
    total_duration_ms: int = Field(..., description="总执行时长")
    total_cost_usd: float = Field(0.0, description="总LLM成本")
    operations_count: int = Field(..., description="操作数量")
    llm_calls_count: int = Field(0, description="LLM调用次数")
    from_version: int = Field(..., description="修改前版本")
    to_version: int = Field(..., description="修改后版本")


class ModificationResult(BaseModel):
    """
    修改结果模型
    
    表示一次完整修改操作的结果。
    
    Attributes:
        success: 是否成功
        report_id: 报告ID
        session_id: 会话ID
        operations: 执行的操作列表
        explanation: 用户友好的说明
        new_markdown_content: 新的Markdown内容
        metadata: 修改元数据
        error_message: 错误信息（如果失败）
    """
    success: bool = Field(..., description="是否成功")
    report_id: str = Field(..., description="报告ID")
    session_id: str = Field(..., description="会话ID")
    operations: List[Operation] = Field(default_factory=list, description="执行的操作")
    explanation: str = Field(..., description="系统响应说明")
    new_markdown_content: str = Field(..., description="新的Markdown内容")
    metadata: ModificationMetadata = Field(..., description="修改元数据")
    error_message: Optional[str] = Field(None, description="错误信息")


# ============================================================================
# API 请求响应模型
# ============================================================================

class ReportModificationRequest(BaseModel):
    """
    报告修改请求模型
    
    客户端提交的修改请求。
    
    Attributes:
        report_id: 报告ID
        user_request: 用户的自然语言修改请求
        session_id: 会话ID（可选，如果不提供则创建新会话）
    """
    report_id: str = Field(..., description="报告ID")
    user_request: str = Field(..., description="用户修改请求")
    session_id: Optional[str] = Field(None, description="会话ID")


class ReportModificationResponse(BaseModel):
    """
    报告修改响应模型
    
    返回给客户端的修改结果。
    
    Attributes:
        success: 是否成功
        session_id: 会话ID
        report_id: 报告ID
        new_version: 新版本号
        explanation: 系统响应说明
        operations_summary: 操作摘要
        markdown_content: 新的Markdown内容
        metadata: 修改元数据
        error: 错误信息
    """
    success: bool = Field(..., description="是否成功")
    session_id: str = Field(..., description="会话ID")
    report_id: str = Field(..., description="报告ID")
    new_version: int = Field(..., description="新版本号")
    explanation: str = Field(..., description="系统响应")
    operations_summary: List[str] = Field(default_factory=list, description="操作摘要列表")
    markdown_content: str = Field(..., description="新Markdown内容")
    metadata: ModificationMetadata = Field(..., description="元数据")
    error: Optional[str] = Field(None, description="错误信息")


class ConversationHistoryResponse(BaseModel):
    """
    对话历史响应模型
    
    返回给客户端的对话历史。
    
    Attributes:2
        session_id: 会话ID
        report_id: 报告ID
        turns: 对话轮次列表
        context_summary: 上下文总结
        current_version: 当前版本号
    """
    session_id: str = Field(..., description="会话ID")
    report_id: str = Field(..., description="报告ID")
    turns: List[ConversationTurn] = Field(default_factory=list, description="对话历史")
    context_summary: Optional[str] = Field(None, description="上下文总结")
    current_version: int = Field(..., description="当前版本号")


class SaveAsTemplateRequest(BaseModel):
    """
    保存为模板请求模型
    
    将修改后的报告保存为新模板。
    
    Attributes:
        report_id: 报告ID
        template_name: 新模板名称
        template_description: 模板描述
    """
    report_id: str = Field(..., description="报告ID")
    template_name: str = Field(..., description="新模板名称")
    template_description: Optional[str] = Field(None, description="模板描述")


class SaveAsTemplateResponse(BaseModel):
    """
    保存为模板响应模型
    
    Attributes:
        success: 是否成功
        template_id: 新模板ID
        message: 响应消息
    """
    success: bool = Field(..., description="是否成功")
    template_id: str = Field(..., description="新模板ID")
    message: str = Field(..., description="响应消息")


# ============================================================================
# 删除章节相关模型
# ============================================================================

class Section(BaseModel):
    """
    章节信息（后端解析生成）
    
    Attributes:
        id: 唯一ID，如 L15
        level: 标题级别 1-6
        title: 标题文本
        path: 完整路径，如 '报告->1、概述->1.1 评分'
        start_line: 起始行号（0-indexed）
        end_line: 结束行号（不包含）
        parent_id: 父章节ID
        subsections_count: 子章节数量
    """
    id: str = Field(..., description="唯一ID")
    level: int = Field(..., description="标题级别 1-6")
    title: str = Field(..., description="标题文本")
    path: str = Field(..., description="完整路径")
    start_line: int = Field(..., description="起始行号")
    end_line: int = Field(..., description="结束行号")
    parent_id: Optional[str] = Field(None, description="父章节ID")
    subsections_count: int = Field(0, description="子章节数量")


class SectionDeleteConfirmation(BaseModel):
    """
    章节删除确认信息（展示给用户）
    
    Attributes:
        section_path: 章节完整路径
        content_preview: 内容预览
        section_id: 内部ID，用于精确删除
        start_line: 起始行号
        end_line: 结束行号
    """
    section_path: str = Field(..., description="章节完整路径")
    content_preview: str = Field(..., description="内容预览（前200字）")
    section_id: str = Field(..., description="内部ID")
    start_line: int = Field(..., description="起始行号")
    end_line: int = Field(..., description="结束行号")


class BatchDeletePlan(BaseModel):
    """
    批量删除计划
    
    Attributes:
        plan_id: 计划ID
        conversation_id: 会话ID
        sections: 待删除章节列表
        total_count: 总章节数
        will_lock_report: 是否会锁定报告
        lock_warning: 锁定警告文本
        alternatives: 替代方案列表
    """
    plan_id: str = Field(..., description="计划ID")
    conversation_id: str = Field(..., description="会话ID")
    sections: List[SectionDeleteConfirmation] = Field(..., description="待删除章节列表")
    total_count: int = Field(..., description="总章节数")
    will_lock_report: bool = Field(True, description="是否会锁定报告")
    lock_warning: str = Field(..., description="锁定警告文本")
    alternatives: List[Dict[str, str]] = Field(
        default_factory=lambda: [
            {
                "action": "regenerate_without_sections",
                "label": "重新生成（排除这些章节）",
                "description": "使用最新数据重新生成报告，但排除指定章节"
            }
        ],
        description="替代方案列表"
    )


class UserDecision(BaseModel):
    """
    用户对单个章节的决策
    
    Attributes:
        section_id: 章节ID
        decision: 决策 execute | skip | reject
    """
    section_id: str = Field(..., description="章节ID")
    decision: str = Field(..., description="execute | skip | reject")


class DeleteExecutionResult(BaseModel):
    """
    删除执行结果
    
    Attributes:
        success: 是否成功
        action_taken: 执行的操作
        deleted_sections: 已删除章节列表
        skipped_sections: 跳过的章节列表
        report_state: 更新后的报告状态
        message: 执行结果消息
        available_operations: 可用操作列表
        unavailable_operations: 不可用操作列表
    """
    success: bool = Field(..., description="是否成功")
    action_taken: str = Field(..., description="delete_and_lock | regenerate_without")
    deleted_sections: List[str] = Field(default_factory=list, description="已删除章节列表")
    skipped_sections: List[str] = Field(default_factory=list, description="跳过的章节列表")
    report_state: Dict[str, Any] = Field(..., description="更新后的报告状态")
    message: str = Field(..., description="执行结果消息")
    available_operations: List[str] = Field(default_factory=list, description="可用操作列表")
    unavailable_operations: List[str] = Field(default_factory=list, description="不可用操作列表")


class PlanDeleteRequest(BaseModel):
    """
    生成删除计划请求
    
    Attributes:
        user_message: 用户删除请求
        conversation_id: 会话ID
    """
    user_message: str = Field(..., description="用户删除请求")
    conversation_id: str = Field(..., description="会话ID")


class ExecuteDeleteRequest(BaseModel):
    """
    执行删除计划请求
    
    Attributes:
        plan_id: 计划ID
        action: delete_and_lock | regenerate_without
        decisions: 用户对每个章节的决策
    """
    plan_id: str = Field(..., description="计划ID")
    action: str = Field(..., description="delete_and_lock | regenerate_without")
    decisions: List[UserDecision] = Field(..., description="用户对每个章节的决策")


# ============================================================================
# 模型更新: 添加前向引用支持
# ============================================================================

# 更新模型以支持前向引用
ModificationIntent.model_rebuild()
Operation.model_rebuild()
OperationStep.model_rebuild()
VariableInfo.model_rebuild()
ReportState.model_rebuild()
ConversationTurn.model_rebuild()
ConversationMemory.model_rebuild()
ModificationResult.model_rebuild()
ModificationMetadata.model_rebuild()

