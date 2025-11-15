"""
参数更新执行策略

本模块实现参数更新操作的具体执行逻辑,包括:
- 更新参数值
- 重新执行依赖变量
- 与ExecutionScheduler集成
"""
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.services.agent.strategies.base import ExecutionStrategy
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    ParameterUpdateDetails,
    ConversationMemory,
    VariableInfo,
    VariableType
)

logger = logging.getLogger(__name__)


class ParameterUpdateStrategy(ExecutionStrategy):
    """
    参数更新执行策略
    
    负责执行参数更新操作,包括:
    1. 更新参数值
    2. 识别依赖变量
    3. 重新执行依赖变量
    4. 更新内存中的状态
    
    Attributes:
        db: 数据库会话
        scheduler: 执行调度器
    """
    
    def __init__(self, db: Session):
        """
        初始化参数更新策略
        
        Args:
            db: 数据库会话
        """
        self.db = db
        # ExecutionScheduler将在执行时根据需要创建
    
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行参数更新操作
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Returns:
            Operation: 执行结果
        """
        start_time = datetime.now()
        
        try:
            # 获取目标变量
            variable_name = step.target_variable
            if not variable_name:
                raise ValueError("缺少目标变量名")
            
            # 检查变量是否存在
            if variable_name not in memory.report_state.variables:
                raise ValueError(f"变量不存在: {variable_name}")
            
            var_info = memory.report_state.variables[variable_name]
            old_value = var_info.value
            
            # 检查是否为重新执行操作
            is_re_execute = step.parameters.get("re_execute", False)
            
            if is_re_execute:
                # 重新执行依赖变量
                logger.info(f"重新执行依赖变量: {variable_name}")
                new_value = await self._re_execute_variable(
                    variable_name,
                    var_info,
                    memory
                )
            else:
                # 更新参数值
                new_value = step.parameters.get("new_value")
                if new_value is None:
                    raise ValueError("缺少新值")
                
                logger.info(f"更新参数 {variable_name}: {old_value} -> {new_value}")
                
                # 直接更新值
                var_info.value = new_value
                var_info.last_updated = datetime.now()
            
            # 找出依赖变量
            dependent_vars = self._find_direct_dependents(variable_name, memory)
            
            # 计算执行时长
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 创建操作详情
            details = ParameterUpdateDetails(
                variable_name=variable_name,
                old_value=old_value,
                new_value=new_value,
                dependent_variables=dependent_vars
            )
            
            logger.info(
                f"参数更新完成: {variable_name}, "
                f"耗时: {duration_ms}ms, "
                f"影响 {len(dependent_vars)} 个依赖变量"
            )
            
            return self._create_operation_result(
                operation_type="update_parameter",
                details=details,
                success=True,
                duration_ms=duration_ms
            )
        
        except Exception as e:
            logger.error(f"参数更新失败: {str(e)}")
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 创建失败的操作结果
            details = ParameterUpdateDetails(
                variable_name=step.target_variable or "unknown",
                old_value=None,
                new_value=None,
                dependent_variables=[]
            )
            
            return self._create_operation_result(
                operation_type="update_parameter",
                details=details,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms
            )
    
    async def _re_execute_variable(
        self,
        variable_name: str,
        var_info: VariableInfo,
        memory: ConversationMemory
    ) -> Any:
        """
        重新执行变量
        
        根据变量的源类型,重新执行获取新值。
        
        Args:
            variable_name: 变量名
            var_info: 变量信息
            memory: 对话记忆
        
        Returns:
            Any: 新的变量值
        """
        source_type = var_info.source
        
        logger.info(f"重新执行变量 {variable_name} (类型: {source_type})")
        
        # 根据不同的源类型执行不同的逻辑
        if source_type == "user_input":
            # 用户输入变量不需要重新执行,保持原值
            logger.warning(f"变量 {variable_name} 是用户输入,无需重新执行")
            return var_info.value
        
        elif source_type == "constant":
            # 常量不需要重新执行
            logger.warning(f"变量 {variable_name} 是常量,无需重新执行")
            return var_info.value
        
        elif source_type in ["sql", "api", "ai_generation", "system", "image", "vision_ai"]:
            # 需要重新执行的变量类型
            # TODO: 集成ExecutionScheduler进行实际执行
            # 目前暂时返回原值
            logger.warning(
                f"变量 {variable_name} 需要重新执行(类型: {source_type}), "
                f"但集成尚未完成,保持原值"
            )
            return var_info.value
        
        else:
            logger.warning(f"未知的变量源类型: {source_type}")
            return var_info.value
    
    def _find_direct_dependents(
        self,
        variable_name: str,
        memory: ConversationMemory
    ) -> List[str]:
        """
        查找直接依赖于指定变量的其他变量
        
        Args:
            variable_name: 变量名
            memory: 对话记忆
        
        Returns:
            List[str]: 依赖变量名列表
        """
        dependents = []
        
        for var_name, var_info in memory.report_state.variables.items():
            # 检查depends_on字段
            depends_on = var_info.metadata.get("depends_on", [])
            if isinstance(depends_on, list) and variable_name in depends_on:
                dependents.append(var_name)
        
        return dependents
    
    def _update_variable_in_template_metadata(
        self,
        variable_name: str,
        new_value: Any,
        memory: ConversationMemory
    ) -> None:
        """
        更新模板元数据中的变量默认值
        
        如果模板被修改,需要同步更新元数据。
        
        Args:
            variable_name: 变量名
            new_value: 新值
            memory: 对话记忆
        """
        if not memory.report_state.template_metadata:
            return
        
        # 查找并更新变量定义
        variables_metadata = memory.report_state.template_metadata.get("variables", {})
        if variable_name in variables_metadata:
            variables_metadata[variable_name]["default_value"] = new_value
            logger.debug(f"更新模板元数据中的变量 {variable_name} 默认值")

