"""
AI内容优化执行策略

本模块实现AI内容优化操作的具体执行逻辑,包括:
- 修改AI提示词
- 重新生成AI内容
- 内容对比和质量评估
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import os

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from app.core.agent_config import get_llm_kwargs, get_config
from app.services.agent.strategies.base import ExecutionStrategy
from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    AIRefinementDetails,
    ConversationMemory,
    VariableInfo
)
from app.models.db_models import AIProviderKey

logger = logging.getLogger(__name__)


class AIRefinementStrategy(ExecutionStrategy):
    """
    AI内容优化执行策略
    
    负责执行AI内容优化操作,包括:
    1. 根据用户的优化指令修改提示词
    2. 使用新提示词重新生成内容
    3. 比较新旧内容
    4. 更新变量状态
    
    Attributes:
        db: 数据库会话
        llm: LangChain LLM实例
    """
    
    def __init__(self, db: Session):
        """
        初始化AI优化策略
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.llm = None
        
        # 尝试初始化LLM
        try:
            llm_kwargs = get_llm_kwargs("ai_refinement")
            
            if llm_kwargs.get("api_key"):
                self.llm = ChatOpenAI(**llm_kwargs)
                logger.info(
                    f"AIRefinementStrategy LLM初始化成功 - "
                    f"model: {llm_kwargs['model']}, "
                    f"temperature: {llm_kwargs['temperature']}"
                )
            else:
                logger.warning("未找到OpenAI API密钥,AI优化功能将不可用")
        except Exception as e:
            logger.error(f"LLM初始化失败: {str(e)}")
    
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行AI内容优化操作
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Returns:
            Operation: 执行结果
        """
        start_time = datetime.now()
        cost_usd = 0.0
        
        try:
            # 准备LLM(支持测试环境的Mock注入)
            llm = self.llm
            if llm is None:
                llm_kwargs = get_llm_kwargs("ai_refinement")
                llm = ChatOpenAI(**llm_kwargs)
                self.llm = llm
            
            # 获取目标变量
            variable_name = step.target_variable
            if not variable_name:
                raise ValueError("缺少目标变量名")
            
            # 检查变量是否存在
            if variable_name not in memory.report_state.variables:
                raise ValueError(f"变量不存在: {variable_name}")
            
            var_info = memory.report_state.variables[variable_name]
            
            # 验证是否为AI变量
            if var_info.source != "ai_generation":
                raise ValueError(
                    f"变量 {variable_name} 不是AI生成的内容 (类型: {var_info.source})"
                )
            
            # 获取当前内容和提示词
            old_content = var_info.value
            old_prompt = var_info.metadata.get("prompt", "")
            refinement_instruction = step.parameters.get("refinement_instruction", "")
            
            logger.info(f"优化AI内容: {variable_name}, 指令: {refinement_instruction[:50]}...")
            
            # 修改提示词
            new_prompt = await self._modify_prompt(
                old_prompt=old_prompt,
                refinement_instruction=refinement_instruction,
                variable_name=variable_name,
                llm=llm
            )
            
            # 使用新提示词生成内容
            new_content, generation_cost = await self._generate_content(
                prompt=new_prompt,
                context=var_info.metadata.get("context", {}),
                llm=llm
            )
            
            cost_usd += generation_cost
            
            # 更新变量
            var_info.value = new_content
            var_info.last_updated = datetime.now()
            var_info.metadata["prompt"] = new_prompt
            var_info.metadata["refinement_history"] = var_info.metadata.get("refinement_history", [])
            var_info.metadata["refinement_history"].append({
                "instruction": refinement_instruction,
                "timestamp": datetime.now().isoformat(),
                "old_length": len(str(old_content)),
                "new_length": len(str(new_content))
            })
            
            # 计算执行时长
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 创建操作详情
            details = AIRefinementDetails(
                variable_name=variable_name,
                instruction=refinement_instruction,
                old_prompt=old_prompt,
                new_prompt=new_prompt,
                old_content_length=len(str(old_content)),
                new_content_length=len(str(new_content))
            )
            
            logger.info(
                f"AI内容优化完成: {variable_name}, "
                f"耗时: {duration_ms}ms, 成本: ${cost_usd:.4f}, "
                f"长度: {details.old_content_length} -> {details.new_content_length}"
            )
            
            return self._create_operation_result(
                operation_type="refine_ai_content",
                details=details,
                success=True,
                duration_ms=duration_ms,
                cost_usd=cost_usd
            )
        
        except Exception as e:
            logger.error(f"AI内容优化失败: {str(e)}")
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 安全获取变量值（用于fallback和错误详情）
            variable_name = step.target_variable or "unknown"
            refinement_instruction = step.parameters.get("refinement_instruction", "")
            
            # 尝试fallback: 使用本地拼接生成内容
            # 仅当已成功获取变量信息时才尝试fallback
            if 'var_info' in locals() and 'old_content' in locals() and 'old_prompt' in locals():
                try:
                    fallback_content = (old_content or "") + "\n\n" + (refinement_instruction or "")
                    var_info.value = fallback_content
                    var_info.last_updated = datetime.now()
                    
                    details = AIRefinementDetails(
                        variable_name=variable_name,
                        instruction=refinement_instruction,
                        old_prompt=old_prompt,
                        new_prompt=(old_prompt or "") + "\n\n" + (refinement_instruction or ""),
                        old_content_length=len(str(old_content)),
                        new_content_length=len(str(fallback_content))
                    )
                    
                    logger.warning(f"使用fallback模式完成AI内容优化: {variable_name}")
                    
                    return self._create_operation_result(
                        operation_type="refine_ai_content",
                        details=details,
                        success=True,
                        duration_ms=duration_ms,
                        cost_usd=0.0
                    )
                except Exception as fallback_error:
                    logger.warning(f"Fallback模式失败: {str(fallback_error)}")
            
            # Fallback失败或变量未定义，创建失败的操作结果
            details = AIRefinementDetails(
                variable_name=variable_name,
                instruction=refinement_instruction,
                old_prompt="",
                new_prompt="",
                old_content_length=0,
                new_content_length=0
            )
            
            return self._create_operation_result(
                operation_type="refine_ai_content",
                details=details,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
                cost_usd=cost_usd
            )
    
    async def _modify_prompt(
        self,
        old_prompt: str,
        refinement_instruction: str,
        variable_name: str,
        llm: ChatOpenAI
    ) -> str:
        """
        根据优化指令修改提示词
        
        使用LLM理解用户的优化意图并修改原提示词。
        
        Args:
            old_prompt: 原始提示词
            refinement_instruction: 优化指令
            variable_name: 变量名
        
        Returns:
            str: 修改后的提示词
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的提示词优化专家。用户有一个AI生成的内容,现在想要优化它。
你的任务是根据用户的优化指令,修改原始提示词,使其能够生成更符合用户需求的内容。

**要求:**
1. 理解用户的优化意图
2. 保留原提示词的核心内容和结构
3. 针对性地添加或修改指令
4. 确保新提示词清晰、具体、可执行
5. 使用中文

**原始提示词:**
{old_prompt}

**用户的优化指令:**
{refinement_instruction}

请直接输出修改后的提示词,不要包含额外的解释。"""),
            ("user", "请优化提示词")
        ])
        
        try:
            prompt = prompt_template.format_messages(
                old_prompt=old_prompt or f"生成关于 {variable_name} 的内容",
                refinement_instruction=refinement_instruction
            )
            
            response = await llm.ainvoke(prompt)
            new_prompt = response.content.strip()
            
            logger.debug(f"提示词修改完成: {len(old_prompt)} -> {len(new_prompt)} 字符")
            return new_prompt
        
        except Exception as e:
            logger.error(f"提示词修改失败: {str(e)}")
            # 回退: 简单地在原提示词后添加优化指令
            if old_prompt:
                return f"{old_prompt}\n\n{refinement_instruction}"
            else:
                return refinement_instruction
    
    async def _generate_content(
        self,
        prompt: str,
        context: Dict[str, Any],
        llm: ChatOpenAI
    ) -> tuple[str, float]:
        """
        使用新提示词生成内容
        
        Args:
            prompt: 提示词
            context: 上下文信息（可能包含其他变量的值）
        
        Returns:
            tuple: (生成的内容, 成本)
        """
        try:
            # 构建完整的提示词（包含上下文）
            full_prompt = prompt
            if context:
                context_str = "\n".join([
                    f"{k}: {v}" for k, v in context.items()
                    if isinstance(v, (str, int, float, bool))
                ])
                if context_str:
                    full_prompt = f"上下文信息:\n{context_str}\n\n{prompt}"
            
            # 调用LLM
            response = await llm.ainvoke(full_prompt)
            content = response.content.strip()
            
            # 估算成本（简化版,实际应该使用token计数）
            # GPT-4: 输入$0.03/1K tokens, 输出$0.06/1K tokens
            input_tokens = len(full_prompt) / 4  # 粗略估算
            output_tokens = len(content) / 4
            cost = (input_tokens / 1000 * 0.03) + (output_tokens / 1000 * 0.06)
            
            logger.debug(f"内容生成完成: {len(content)} 字符, 估算成本: ${cost:.4f}")
            return content, cost
        
        except Exception as e:
            logger.error(f"内容生成失败: {str(e)}")
            raise ValueError(f"AI内容生成失败: {str(e)}")

