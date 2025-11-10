"""
执行调度器模块（基于DAG有向无环图）

功能说明：
- 根据变量依赖关系构建DAG
- 使用拓扑排序确定执行顺序
- 支持并行执行无依赖关系的变量
- 管理所有类型的变量执行器
- 处理执行失败和默认值
"""
from typing import Dict, List, Set, Any, Optional
import asyncio
import networkx as nx
from app.core.models import (
    VariableMetadata, VariableSource, VariableExecutionResult,
    VariableStatus
)
from app.services.context import ExecutionContext
from app.services.execution_logger import execution_logger
from app.executors.base import BaseVariableExecutor
from app.executors.user_input import UserInputExecutor
from app.executors.system import SystemExecutor
from app.executors.sql import SqlExecutor
from app.executors.api import ApiExecutor
from app.executors.ai import AiExecutor
from app.executors.constant import ConstantExecutor
from app.executors.image import ImageExecutor
from app.executors.vision_ai import VisionAiExecutor
from app.core.exceptions import DependencyError


class ExecutionScheduler:
    """
    执行调度器
    
    核心职责：
    1. 构建变量依赖图（DAG）
    2. 拓扑排序，确定执行顺序
    3. 批量并行执行无依赖关系的变量
    4. 管理执行器工厂（创建不同类型的执行器）
    5. 监控执行进度和错误处理
    
    执行策略：
    - 常量变量优先执行（无依赖，自动注入）
    - 其他变量按依赖关系分批执行
    - 同一批次内的变量并行执行
    - 失败的必需变量会中断整个流程
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, openai_api_base: Optional[str] = None):
        """
        初始化调度器
        
        Args:
            openai_api_key: OpenAI API密钥（用于AI生成变量）
            openai_api_base: OpenAI API基础URL（可自定义，如硅基流动）
        """
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base
        
    def build_dag(self, metadata: Dict[str, VariableMetadata]) -> nx.DiGraph:
        """
        根据变量依赖关系构建有向无环图（DAG）
        
        构建步骤：
        1. 创建图对象
        2. 添加所有变量作为节点
        3. 根据dependencies添加边（从依赖指向被依赖者）
        4. 检测循环依赖
        
        示例：
            变量A依赖B和C，变量B依赖C
            图结构：C -> B -> A
            执行顺序：C, B, A
        
        Args:
            metadata: 变量元数据字典 {变量名: VariableMetadata}
        
        Returns:
            NetworkX DiGraph: 有向无环图对象
            
        Raises:
            DependencyError: 依赖的变量不存在，或存在循环依赖
        """
        G = nx.DiGraph()
        
        # 步骤1：添加所有变量作为图的节点
        for var_name in metadata.keys():
            G.add_node(var_name)
        
        # 步骤2：根据依赖关系添加边
        for var_name, var_meta in metadata.items():
            if var_meta.dependencies:
                for dep in var_meta.dependencies:
                    # 检查依赖的变量是否存在
                    if dep not in metadata:
                        raise DependencyError(
                            f"Variable '{var_name}' depends on undefined variable '{dep}'"
                        )
                    # 添加边：从依赖变量指向当前变量
                    # 例如：A依赖B，则添加边 B -> A
                    G.add_edge(dep, var_name)
        
        # 步骤3：检查是否存在循环依赖
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            raise DependencyError(f"Circular dependency detected: {cycles}")
        
        return G
        
    def get_execution_batches(self, dag: nx.DiGraph) -> List[List[str]]:
        """
        使用拓扑排序获取执行批次
        
        批次规则：
        - 同一批次内的变量无依赖关系，可并行执行
        - 后续批次依赖前面批次的结果
        - 使用NetworkX的topological_generations算法
        
        示例：
            DAG: C -> B -> A, D -> A
            批次: [[C, D], [B], [A]]
            解释: C和D无依赖可并行，B依赖C，A依赖B和D
        
        Args:
            dag: 有向无环图对象
        
        Returns:
            List[List[str]]: 批次列表，每个批次是可并行执行的变量名列表
        """
        # 使用拓扑生成算法（按层级分组）
        batches = list(nx.topological_generations(dag))
        return batches
        
    def create_executor(self, var_name: str, metadata: VariableMetadata,
                       context: ExecutionContext) -> BaseVariableExecutor:
        """
        执行器工厂方法：根据变量来源创建相应的执行器
        
        支持的执行器类型：
        - USER_INPUT: 用户输入执行器
        - SYSTEM: 系统函数执行器（时间、UUID等）
        - SQL: SQL查询执行器
        - API: 外部API调用执行器
        - AI_GENERATION: AI生成执行器（OpenAI）
        - CONSTANT: 常量执行器
        - IMAGE: 图片处理执行器
        - VISION_AI: 视觉AI执行器（图片识别）
        
        Args:
            var_name: 变量名
            metadata: 变量元数据
            context: 执行上下文
        
        Returns:
            BaseVariableExecutor: 对应类型的执行器实例
            
        Raises:
            ValueError: 不支持的变量来源类型
        """
        source = metadata.source
        
        if source == VariableSource.USER_INPUT:
            return UserInputExecutor(var_name, metadata, context)
        elif source == VariableSource.SYSTEM:
            return SystemExecutor(var_name, metadata, context)
        elif source == VariableSource.SQL:
            return SqlExecutor(var_name, metadata, context)
        elif source == VariableSource.API:
            return ApiExecutor(var_name, metadata, context)
        elif source == VariableSource.AI_GENERATION:
            return AiExecutor(var_name, metadata, context, 
                            openai_api_key=self.openai_api_key,
                            openai_api_base=self.openai_api_base)
        elif source == VariableSource.CONSTANT:
            return ConstantExecutor(var_name, metadata, context)
        elif source == VariableSource.IMAGE:
            return ImageExecutor(var_name, metadata, context)
        elif source == VariableSource.VISION_AI:
            return VisionAiExecutor(var_name, metadata, context,
                                   openai_api_key=self.openai_api_key,
                                   openai_api_base=self.openai_api_base)
        else:
            raise ValueError(f"Unknown variable source: {source}")
            
    async def execute_batch(self, batch: List[str], context: ExecutionContext) -> List[VariableExecutionResult]:
        """
        并行执行一批变量
        
        执行流程：
        1. 为批次中的每个变量创建执行器
        2. 使用asyncio.gather并行执行所有任务
        3. 收集并返回所有执行结果
        
        注意：
        - 批次内的变量无依赖关系，可安全并行
        - 所有变量同时开始执行
        - 等待所有变量执行完成后返回
        
        Args:
            batch: 变量名列表
            context: 执行上下文（包含已执行的变量值）
            
        Returns:
            List[VariableExecutionResult]: 执行结果列表
        """
        tasks = []
        
        # 为每个变量创建执行任务
        for var_name in batch:
            metadata = context.metadata[var_name]
            executor = self.create_executor(var_name, metadata, context)
            tasks.append(executor.execute())
        
        # 并行执行所有任务（使用asyncio.gather）
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
        
    async def execute_all(self, context: ExecutionContext,
                         progress_callback: Optional[callable] = None) -> Dict[str, VariableExecutionResult]:
        """
        执行上下文中的所有变量（遵循依赖关系）
        
        执行策略（三阶段）：
        1. 预执行阶段：执行所有CONSTANT变量（无依赖，自动注入）
        2. DAG构建阶段：为非常量变量构建依赖图
        3. 批量执行阶段：按拓扑顺序批量并行执行变量
        
        进度回调：
        - 每个变量执行前调用：callback(var_name, RUNNING, None)
        - 每个变量执行后调用：callback(var_name, SUCCESS/FAILED, result)
        - 可用于实时更新UI、WebSocket通知等
        
        错误处理：
        - 常量失败：记录警告，继续执行
        - 必需变量失败且无默认值：中断执行，抛出异常
        - 可选变量失败：记录错误，继续执行
        
        Args:
            context: 执行上下文（包含元数据、用户输入等）
            progress_callback: 进度回调函数
                             签名: callback(var_name: str, status: VariableStatus, result: VariableExecutionResult)
            
        Returns:
            Dict[str, VariableExecutionResult]: 所有变量的执行结果字典
        """
        all_results = {}
        
        # 阶段1：预执行所有CONSTANT变量
        # 常量变量无依赖，可以提前执行并注入到上下文中
        execution_logger.info(
            context.task_id,
            "Pre-executing constant variables for auto-injection"
        )
        
        for var_name, metadata in context.metadata.items():
            if metadata.source == VariableSource.CONSTANT:
                # Notify start if callback provided
                if progress_callback:
                    await progress_callback(var_name, VariableStatus.RUNNING, None)
                
                try:
                    executor = ConstantExecutor(var_name, metadata, context)
                    result = await executor.execute()
                    all_results[var_name] = result
                    
                    # Notify completion
                    if progress_callback:
                        await progress_callback(var_name, result.status, result)
                    
                    # Log warning if constant failed but continue execution
                    if result.status == VariableStatus.FAILED:
                        execution_logger.warning(
                            context.task_id,
                            f"Constant variable '{var_name}' failed: {result.error}",
                            variable_name=var_name
                        )
                except Exception as e:
                    execution_logger.error(
                        context.task_id,
                        f"Failed to pre-execute constant '{var_name}': {str(e)}",
                        variable_name=var_name
                    )
                    # Create failed result but continue
                    result = VariableExecutionResult(
                        variable_name=var_name,
                        status=VariableStatus.FAILED,
                        error=str(e)
                    )
                    all_results[var_name] = result
                    if progress_callback:
                        await progress_callback(var_name, result.status, result)
        
        # Phase 2: Filter non-constant variables for DAG
        non_constant_metadata = {
            name: meta 
            for name, meta in context.metadata.items() 
            if meta.source != VariableSource.CONSTANT
        }
        
        execution_logger.info(
            context.task_id,
            f"Building DAG for {len(non_constant_metadata)} non-constant variables"
        )
        
        # Phase 3: Build DAG and execute non-constant variables
        if non_constant_metadata:
            # Build DAG (only for non-constant variables)
            dag = self.build_dag(non_constant_metadata)
            
            # Get execution batches
            batches = self.get_execution_batches(dag)
            
            # Execute batches sequentially, variables within batch in parallel
            for batch_idx, batch in enumerate(batches):
                # Notify batch start
                for var_name in batch:
                    if progress_callback:
                        await progress_callback(var_name, VariableStatus.RUNNING, None)
                
                # Execute batch
                batch_results = await self.execute_batch(batch, context)
                
                # Process results
                for result in batch_results:
                    all_results[result.variable_name] = result
                    
                    # Notify completion or failure
                    if progress_callback:
                        await progress_callback(
                            result.variable_name,
                            result.status,
                            result
                        )
                    
                    # Stop execution if required variable failed
                    if result.status == VariableStatus.FAILED:
                        metadata = context.metadata[result.variable_name]
                        if metadata.required and metadata.default is None:
                            # Fail fast for required variables without default
                            raise Exception(
                                f"Required variable '{result.variable_name}' failed: {result.error}"
                            )
        
        return all_results

