"""
查询策略

处理查询类操作，如显示报告内容、列出参数等。
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
    ConversationMemory,
    QueryDetails
)

logger = logging.getLogger(__name__)


class QueryStrategy(ExecutionStrategy):
    """
    查询操作执行策略
    
    处理各种查询操作，如：
    - show_content: 显示报告内容
    - list_variables: 列出所有变量
    - show_parameters: 显示参数列表
    - show_sections: 显示章节结构
    - get_statistics: 获取统计信息
    """
    
    def __init__(self, db: Session):
        """
        初始化查询策略
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行查询操作
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Returns:
            Operation: 操作结果
        """
        start_time = datetime.now()
        
        try:
            query_type = step.parameters.get("query_type", "general_query")
            query_details = step.parameters.get("query_details", {})
            
            logger.info(f"执行查询操作: {query_type}")
            
            # 根据查询类型执行不同的查询
            query_result = self._execute_query(query_type, memory, query_details)
            
            # 计算执行时长
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 创建查询详情
            details = QueryDetails(
                query_type=query_type,
                query_result=query_result,
                result_format="markdown"
            )
            
            return self._create_operation_result(
                operation_type=OperationType.QUERY,
                details=details,
                success=True,
                duration_ms=duration_ms
            )
        
        except Exception as e:
            logger.error(f"查询操作失败: {str(e)}", exc_info=True)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 返回失败结果
            details = QueryDetails(
                query_type=step.parameters.get("query_type", "unknown"),
                query_result=None,
                result_format="error"
            )
            
            return self._create_operation_result(
                operation_type=OperationType.QUERY,
                details=details,
                success=False,
                error_message=f"查询失败: {str(e)}",
                duration_ms=duration_ms
            )
    
    def _execute_query(
        self,
        query_type: str,
        memory: ConversationMemory,
        query_details: Dict[str, Any]
    ) -> Any:
        """
        执行具体的查询操作
        
        Args:
            query_type: 查询类型
            memory: 对话记忆
            query_details: 查询详情
        
        Returns:
            Any: 查询结果
        """
        if query_type == "show_content":
            return self._show_content(memory)
        
        elif query_type == "list_variables":
            return self._list_variables(memory)
        
        elif query_type == "show_parameters":
            return self._show_parameters(memory)
        
        elif query_type == "show_sections":
            return self._show_sections(memory)
        
        elif query_type == "get_statistics":
            return self._get_statistics(memory)
        
        elif query_type == "show_history":
            return self._show_history(memory)
        
        else:
            # 通用查询
            return self._general_query(memory, query_details)
    
    def _show_content(self, memory: ConversationMemory) -> str:
        """显示报告内容"""
        content = memory.report_state.markdown_content
        
        # 添加统计信息
        char_count = len(content)
        line_count = content.count('\n') + 1
        
        result = f"# 当前报告内容\n\n"
        result += f"**统计信息**: {char_count} 字符, {line_count} 行\n\n"
        result += f"---\n\n{content}"
        
        return result
    
    def _list_variables(self, memory: ConversationMemory) -> str:
        """列出所有变量"""
        variables = memory.report_state.variables
        
        if not variables:
            return "当前报告没有变量。"
        
        result = f"# 变量列表\n\n共 {len(variables)} 个变量：\n\n"
        
        for name, var_info in variables.items():
            result += f"## {name}\n"
            result += f"- **类型**: {var_info.variable_type}\n"
            result += f"- **来源**: {var_info.source}\n"
            
            # 显示值（如果不太长）
            value_str = str(var_info.value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            result += f"- **值**: {value_str}\n"
            
            # 显示依赖关系
            dependencies = var_info.metadata.get("dependencies", [])
            if dependencies:
                result += f"- **依赖**: {', '.join(dependencies)}\n"
            
            result += "\n"
        
        return result
    
    def _show_parameters(self, memory: ConversationMemory) -> str:
        """显示参数列表"""
        variables = memory.report_state.variables
        
        # 过滤出用户输入参数
        params = {
            name: var for name, var in variables.items()
            if var.source == "user_input"
        }
        
        if not params:
            return "当前报告没有用户输入参数。"
        
        result = f"# 参数列表\n\n共 {len(params)} 个参数：\n\n"
        
        for name, var_info in params.items():
            result += f"- **{name}**: {var_info.value}\n"
        
        return result
    
    def _show_sections(self, memory: ConversationMemory) -> str:
        """显示章节结构"""
        content = memory.report_state.markdown_content
        
        # 解析章节结构
        sections = []
        lines = content.split('\n')
        
        for line in lines:
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                sections.append((level, title))
        
        if not sections:
            return "当前报告没有章节标题。"
        
        result = f"# 章节结构\n\n共 {len(sections)} 个章节：\n\n"
        
        for level, title in sections:
            indent = "  " * (level - 1)
            result += f"{indent}- {title}\n"
        
        return result
    
    def _get_statistics(self, memory: ConversationMemory) -> str:
        """获取统计信息"""
        content = memory.report_state.markdown_content
        variables = memory.report_state.variables
        
        # 统计信息
        char_count = len(content)
        word_count = len(content.split())
        line_count = content.count('\n') + 1
        
        # 章节统计
        section_count = content.count('\n#')
        
        # 变量统计
        var_count = len(variables)
        param_count = sum(1 for v in variables.values() if v.source == "user_input")
        ai_count = sum(1 for v in variables.values() if v.source == "ai_generation")
        
        result = f"# 报告统计信息\n\n"
        result += f"## 内容统计\n"
        result += f"- **字符数**: {char_count}\n"
        result += f"- **词数**: {word_count}\n"
        result += f"- **行数**: {line_count}\n"
        result += f"- **章节数**: {section_count}\n\n"
        
        result += f"## 变量统计\n"
        result += f"- **总变量数**: {var_count}\n"
        result += f"- **用户参数**: {param_count}\n"
        result += f"- **AI生成变量**: {ai_count}\n\n"
        
        result += f"## 报告信息\n"
        result += f"- **报告ID**: {memory.report_id}\n"
        result += f"- **当前版本**: {memory.current_version}\n"
        result += f"- **模板ID**: {memory.report_state.template_id}\n"
        result += f"- **编辑模式**: {memory.report_state.edit_mode}\n"
        
        return result
    
    def _show_history(self, memory: ConversationMemory) -> str:
        """显示修改历史"""
        history = memory.conversation_history
        
        if not history:
            return "暂无修改历史。"
        
        result = f"# 修改历史\n\n共 {len(history)} 次修改：\n\n"
        
        for turn in history:
            result += f"## 第 {turn.turn_number} 次修改\n"
            result += f"- **用户请求**: {turn.user_request}\n"
            result += f"- **操作数**: {len(turn.operations)}\n"
            result += f"- **版本**: v{turn.report_version}\n"
            result += f"- **时间**: {turn.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return result
    
    def _general_query(
        self,
        memory: ConversationMemory,
        query_details: Dict[str, Any]
    ) -> str:
        """通用查询"""
        # 默认返回报告基本信息
        return f"报告ID: {memory.report_id}, 版本: {memory.current_version}"
