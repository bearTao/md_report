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
            # 检查报告是否锁定
            if not memory.report_state.is_editable():
                raise ValueError(
                    f"报告已锁定为静态版本（锁定时间：{memory.report_state.locked_at.strftime('%Y-%m-%d %H:%M')}），"
                    f"无法修改参数。如需修改参数，请使用'重新生成'功能。"
                )
            
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
            # 使用ExecutionScheduler重新执行该变量
            from app.core.models import VariableMetadata, VariableSource
            
            # 从报告状态中提取所有用户输入参数和构建完整的 metadata
            user_inputs = {}
            all_metadata = {}
            
            for var_name, var in memory.report_state.variables.items():
                # 收集用户输入参数的值
                if var.source == "user_input" and var.value is not None:
                    user_inputs[var_name] = var.value
                
                # 为每个变量构建完整的 VariableMetadata
                # 关键：将 var.source 和 var.metadata 合并
                try:
                    # 复制 metadata 字典，避免修改原始数据
                    meta_dict = dict(var.metadata) if var.metadata else {}
                    
                    # 确保 source 字段存在（从 var.source 获取）
                    if "source" not in meta_dict:
                        meta_dict["source"] = var.source
                    
                    # 确保基础必需字段存在
                    if "type" not in meta_dict:
                        meta_dict["type"] = "string"
                    if "description" not in meta_dict:
                        meta_dict["description"] = f"Variable {var_name}"
                    
                    # 创建 VariableMetadata 对象
                    all_metadata[var_name] = VariableMetadata(**meta_dict)
                    
                except Exception as e:
                    logger.warning(f"解析变量 {var_name} 的 metadata 失败: {e}，使用默认配置")
                    # 创建最小可用的 metadata
                    all_metadata[var_name] = VariableMetadata(
                        type="string",
                        source=VariableSource(var.source) if var.source in [s.value for s in VariableSource] else VariableSource.USER_INPUT,
                        description=f"Variable {var_name}",
                        required=False
                    )
            
            logger.info(f"重新执行变量 {variable_name}, user_inputs: {list(user_inputs.keys())}, metadata_count: {len(all_metadata)}")
            
            # 创建执行上下文
            context = ExecutionContext(
                task_id=f"reexec_{memory.session_id}",
                template_id=memory.report_state.template_id,
                user_inputs=user_inputs,
                metadata=all_metadata  # 传递所有变量的完整 metadata
            )
            
            # 使用调度器重新执行
            scheduler = ExecutionScheduler()
            results = await scheduler.execute_all(context)
            result = results.get(variable_name)
            
            if result and result.value is not None:
                var_info.value = result.value
                var_info.last_updated = datetime.now()
                logger.info(f"变量 {variable_name} 重新执行成功，获得新值")
                return var_info.value
            elif result and result.status == "failed":
                logger.error(f"变量 {variable_name} 重新执行失败: {result.error}")
                raise Exception(f"重新执行变量失败: {result.error}")
            else:
                logger.warning(f"变量 {variable_name} 重新执行未获得新值,保留原值")
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
            # 检查dependencies字段
            dependencies = var_info.metadata.get("dependencies", [])
            if isinstance(dependencies, list) and variable_name in dependencies:
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

