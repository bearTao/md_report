"""Execution scheduler with DAG orchestration - P0"""
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
    Orchestrates variable execution based on dependency graph (DAG)
    Executes variables in topological order with parallelization
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, openai_api_base: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base
        
    def build_dag(self, metadata: Dict[str, VariableMetadata]) -> nx.DiGraph:
        """
        Build directed acyclic graph from variable dependencies
        
        Returns:
            NetworkX DiGraph
        """
        G = nx.DiGraph()
        
        # Add all variables as nodes
        for var_name in metadata.keys():
            G.add_node(var_name)
        
        # Add edges for dependencies
        for var_name, var_meta in metadata.items():
            if var_meta.dependencies:
                for dep in var_meta.dependencies:
                    if dep not in metadata:
                        raise DependencyError(
                            f"Variable '{var_name}' depends on undefined variable '{dep}'"
                        )
                    # Edge from dependency to dependent
                    G.add_edge(dep, var_name)
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            raise DependencyError(f"Circular dependency detected: {cycles}")
        
        return G
        
    def get_execution_batches(self, dag: nx.DiGraph) -> List[List[str]]:
        """
        Get execution batches using topological sort
        Variables in the same batch can be executed in parallel
        
        Returns:
            List of batches, each batch is a list of variable names
        """
        # Topological generations (layers)
        batches = list(nx.topological_generations(dag))
        return batches
        
    def create_executor(self, var_name: str, metadata: VariableMetadata,
                       context: ExecutionContext) -> BaseVariableExecutor:
        """
        Factory method to create appropriate executor for variable
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
        Execute a batch of variables in parallel
        
        Args:
            batch: List of variable names to execute
            context: Execution context
            
        Returns:
            List of execution results
        """
        tasks = []
        
        for var_name in batch:
            metadata = context.metadata[var_name]
            executor = self.create_executor(var_name, metadata, context)
            tasks.append(executor.execute())
        
        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
        
    async def execute_all(self, context: ExecutionContext,
                         progress_callback: Optional[callable] = None) -> Dict[str, VariableExecutionResult]:
        """
        Execute all variables in context respecting dependencies
        
        Execution phases:
        1. Pre-execute all CONSTANT variables (auto-injected, no dependencies needed)
        2. Build DAG for non-constant variables
        3. Execute non-constant variables in topological order
        
        Args:
            context: Execution context with metadata and inputs
            progress_callback: Optional callback for progress updates
                             Signature: callback(var_name, status, result)
            
        Returns:
            Dictionary of all execution results
        """
        all_results = {}
        
        # Phase 1: Pre-execute all CONSTANT variables
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

