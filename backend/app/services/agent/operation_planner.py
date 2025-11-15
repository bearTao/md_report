"""
操作规划器

本模块负责将解析的意图转换为具体的执行步骤,包括:
- 依赖关系分析
- 执行顺序规划
- 参数验证
"""
from typing import List, Dict, Any, Set
import logging

from app.schemas.modification_schemas import (
    ModificationIntent,
    OperationStep,
    OperationType,
    ConversationMemory,
    VariableInfo
)

logger = logging.getLogger(__name__)


class OperationPlanner:
    """
    操作规划器类
    
    将解析的意图转换为具体的执行步骤,并处理依赖关系。
    
    主要职责:
    - 将意图转换为操作步骤
    - 分析变量依赖关系
    - 规划执行顺序
    - 验证操作的可行性
    """
    
    def __init__(self):
        """初始化操作规划器"""
        pass
    
    def create_plan(
        self,
        intents: List[ModificationIntent],
        memory: ConversationMemory
    ) -> List[OperationStep]:
        """
        创建操作计划
        
        根据意图列表和当前状态,生成具体的执行步骤。
        
        Args:
            intents: 意图列表
            memory: 对话记忆
        
        Returns:
            List[OperationStep]: 操作步骤列表
        
        Raises:
            ValueError: 如果意图无效或存在冲突
        """
        steps = []
        step_number = 1
        
        for intent in intents:
            if intent.intent_type == "update_parameter":
                # 参数更新类型
                param_steps = self._plan_parameter_update(
                    intent, memory, step_number
                )
                steps.extend(param_steps)
                step_number += len(param_steps)
            
            elif intent.intent_type == "refine_ai_content":
                # AI内容优化类型
                ai_step = self._plan_ai_refinement(
                    intent, memory, step_number
                )
                steps.append(ai_step)
                step_number += 1
            
            elif intent.intent_type in ["add_section", "modify_section", "remove_section"]:
                # 模板修改类型
                template_step = self._plan_template_modification(
                    intent, memory, step_number
                )
                steps.append(template_step)
                step_number += 1
            
            else:
                logger.warning(f"未知的意图类型: {intent.intent_type}")
        
        logger.info(f"生成了 {len(steps)} 个操作步骤")
        return steps
    
    def _plan_parameter_update(
        self,
        intent: ModificationIntent,
        memory: ConversationMemory,
        start_step: int
    ) -> List[OperationStep]:
        """
        规划参数更新操作
        
        包括主参数更新和依赖变量的重新执行。
        
        Args:
            intent: 参数更新意图
            memory: 对话记忆
            start_step: 起始步骤编号
        
        Returns:
            List[OperationStep]: 操作步骤列表
        """
        steps = []
        
        if not intent.target_variable:
            raise ValueError("参数更新意图缺少target_variable")
        
        # 验证变量是否存在
        if intent.target_variable not in memory.report_state.variables:
            # 变量不存在,可能是新变量或变量名识别错误
            # 尝试模糊匹配
            matched_var = self._fuzzy_match_variable(
                intent.target_variable,
                list(memory.report_state.variables.keys())
            )
            
            if matched_var:
                logger.info(f"模糊匹配变量: {intent.target_variable} -> {matched_var}")
                intent.target_variable = matched_var
            else:
                raise ValueError(
                    f"变量不存在: {intent.target_variable}。"
                    f"已知变量: {', '.join(memory.report_state.variables.keys())}"
                )
        
        # 步骤1: 更新参数值
        update_step = OperationStep(
            step_number=start_step,
            operation_type=OperationType.UPDATE_PARAMETER,
            description=f"更新参数 {intent.target_variable} 的值",
            target_variable=intent.target_variable,
            parameters={
                "new_value": intent.new_value,
                "old_value": memory.report_state.variables[intent.target_variable].value
            }
        )
        steps.append(update_step)
        
        # 步骤2-N: 找出依赖变量并重新执行
        dependent_vars = self._find_dependent_variables(
            intent.target_variable,
            memory
        )
        
        if dependent_vars:
            logger.info(
                f"参数 {intent.target_variable} 有 {len(dependent_vars)} 个依赖变量: "
                f"{', '.join(dependent_vars)}"
            )
            
            # 为每个依赖变量创建重新执行步骤
            for idx, dep_var in enumerate(dependent_vars, start=1):
                dep_step = OperationStep(
                    step_number=start_step + idx,
                    operation_type=OperationType.UPDATE_PARAMETER,
                    description=f"重新执行依赖变量 {dep_var}",
                    target_variable=dep_var,
                    parameters={
                        "re_execute": True,
                        "reason": f"依赖参数 {intent.target_variable} 已更新"
                    }
                )
                steps.append(dep_step)
        
        return steps
    
    def _plan_ai_refinement(
        self,
        intent: ModificationIntent,
        memory: ConversationMemory,
        step_number: int
    ) -> OperationStep:
        """
        规划AI内容优化操作
        
        Args:
            intent: AI优化意图
            memory: 对话记忆
            step_number: 步骤编号
        
        Returns:
            OperationStep: 操作步骤
        """
        if not intent.target_variable:
            # 如果没有指定变量,尝试找到最近的AI生成变量
            ai_variables = [
                name for name, var in memory.report_state.variables.items()
                if var.source == "ai_generation"
            ]
            
            if ai_variables:
                intent.target_variable = ai_variables[-1]  # 使用最后一个AI变量
                logger.info(f"自动选择AI变量: {intent.target_variable}")
            else:
                raise ValueError("没有找到可优化的AI生成内容")
        
        # 验证变量是否为AI类型
        var_info = memory.report_state.variables.get(intent.target_variable)
        if not var_info:
            raise ValueError(f"变量不存在: {intent.target_variable}")
        
        if var_info.source != "ai_generation":
            raise ValueError(
                f"变量 {intent.target_variable} 不是AI生成的内容,"
                f"无法进行AI优化(当前类型: {var_info.source})"
            )
        
        return OperationStep(
            step_number=step_number,
            operation_type=OperationType.REFINE_AI_CONTENT,
            description=f"优化AI内容: {intent.target_variable}",
            target_variable=intent.target_variable,
            parameters={
                "refinement_instruction": intent.refinement_instruction,
                "current_prompt": var_info.metadata.get("prompt", ""),
                "current_content": var_info.value
            }
        )
    
    def _plan_template_modification(
        self,
        intent: ModificationIntent,
        memory: ConversationMemory,
        step_number: int
    ) -> OperationStep:
        """
        规划模板修改操作
        
        Args:
            intent: 模板修改意图
            memory: 对话记忆
            step_number: 步骤编号
        
        Returns:
            OperationStep: 操作步骤
        """
        operation_type_map = {
            "add_section": OperationType.ADD_SECTION,
            "modify_section": OperationType.MODIFY_SECTION,
            "remove_section": OperationType.REMOVE_SECTION
        }
        
        operation_type = operation_type_map.get(intent.intent_type)
        if not operation_type:
            raise ValueError(f"未知的模板修改类型: {intent.intent_type}")
        
        description_map = {
            "add_section": f"添加新章节: {intent.section_description}",
            "modify_section": f"修改章节 {intent.target_section}: {intent.section_description}",
            "remove_section": f"删除章节: {intent.target_section}"
        }
        
        return OperationStep(
            step_number=step_number,
            operation_type=operation_type,
            description=description_map.get(intent.intent_type, "模板修改"),
            target_variable=None,
            parameters={
                "section_name": intent.target_section,
                "section_description": intent.section_description,
                "modification_type": intent.intent_type
            }
        )
    
    def _find_dependent_variables(
        self,
        variable_name: str,
        memory: ConversationMemory
    ) -> List[str]:
        """
        查找依赖于指定变量的其他变量
        
        使用简单的依赖检测:检查变量元数据中的depends_on字段。
        
        Args:
            variable_name: 变量名
            memory: 对话记忆
        
        Returns:
            List[str]: 依赖变量名列表（按拓扑排序）
        """
        dependent_vars = []
        
        # 遍历所有变量,检查依赖关系
        for var_name, var_info in memory.report_state.variables.items():
            # 检查元数据中的depends_on字段
            depends_on = var_info.metadata.get("depends_on", [])
            if isinstance(depends_on, list) and variable_name in depends_on:
                dependent_vars.append(var_name)
        
        # 执行拓扑排序,确保依赖顺序正确
        sorted_vars = self._topological_sort(dependent_vars, memory)
        
        return sorted_vars
    
    def _topological_sort(
        self,
        variables: List[str],
        memory: ConversationMemory
    ) -> List[str]:
        """
        对变量进行拓扑排序
        
        确保变量按照依赖关系的正确顺序执行。
        
        Args:
            variables: 变量名列表
            memory: 对话记忆
        
        Returns:
            List[str]: 排序后的变量名列表
        """
        # 简单实现:基于依赖深度排序
        def get_depth(var_name: str, visited: Set[str] = None) -> int:
            """递归计算变量的依赖深度"""
            if visited is None:
                visited = set()
            
            if var_name in visited:
                return 0  # 避免循环依赖
            
            visited.add(var_name)
            
            var_info = memory.report_state.variables.get(var_name)
            if not var_info:
                return 0
            
            depends_on = var_info.metadata.get("depends_on", [])
            if not depends_on:
                return 0
            
            # 递归计算依赖的最大深度
            max_depth = 0
            for dep in depends_on:
                if isinstance(dep, str):
                    depth = get_depth(dep, visited.copy())
                    max_depth = max(max_depth, depth)
            
            return max_depth + 1
        
        # 计算每个变量的深度并排序
        var_depths = [(var, get_depth(var)) for var in variables]
        var_depths.sort(key=lambda x: x[1])
        
        return [var for var, _ in var_depths]
    
    def _fuzzy_match_variable(
        self,
        target: str,
        candidates: List[str],
        threshold: float = 0.6
    ) -> Optional[str]:
        """
        模糊匹配变量名
        
        用于处理变量名识别不准确的情况。
        
        Args:
            target: 目标变量名
            candidates: 候选变量名列表
            threshold: 相似度阈值（0-1）
        
        Returns:
            Optional[str]: 匹配的变量名,如果没有匹配则返回None
        """
        if not candidates:
            return None
        
        # 简单的字符串相似度匹配
        best_match = None
        best_score = 0.0
        
        target_lower = target.lower()
        
        for candidate in candidates:
            candidate_lower = candidate.lower()
            
            # 完全匹配
            if target_lower == candidate_lower:
                return candidate
            
            # 包含关系
            if target_lower in candidate_lower or candidate_lower in target_lower:
                score = min(len(target_lower), len(candidate_lower)) / max(len(target_lower), len(candidate_lower))
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        # 返回最佳匹配（如果超过阈值）
        if best_score >= threshold:
            return best_match
        
        return None


from typing import Optional

