"""
变量执行器基类模块

功能说明：
- 定义所有变量执行器的抽象基类
- 实现变量执行的通用逻辑（计时、错误处理、日志记录）
- 管理变量依赖检查和任务取消检测
- 支持默认值回退机制
"""
from abc import ABC, abstractmethod
from typing import Any
import time
from app.core.models import VariableMetadata, VariableExecutionResult, VariableStatus
from app.services.context import ExecutionContext
from app.core.exceptions import TaskCancelledException
from app.services.execution_logger import execution_logger


class BaseVariableExecutor(ABC):
    """
    变量执行器抽象基类
    
    所有类型的变量执行器（SQL、AI、API等）都继承自这个类
    
    职责：
    1. 统一的执行流程控制
    2. 错误处理和默认值回退
    3. 执行时间统计
    4. 日志记录
    5. 任务取消检测
    """
    
    def __init__(self, variable_name: str, metadata: VariableMetadata, context: ExecutionContext):
        """
        初始化变量执行器
        
        Args:
            variable_name: 变量名称
            metadata: 变量元数据（包含source、type、dependencies等）
            context: 执行上下文（包含已执行的变量值）
        """
        self.variable_name = variable_name
        self.metadata = metadata
        self.context = context
        
    async def execute(self) -> VariableExecutionResult:
        """
        执行变量（通用执行流程）
        
        执行流程：
        1. 记录开始时间
        2. 检查任务是否被取消
        3. 检查依赖变量是否已就绪
        4. 调用子类实现的_execute_impl()执行具体逻辑
        5. 将结果存入执行上下文
        6. 处理错误和默认值
        7. 记录执行结果和耗时
        
        Returns:
            VariableExecutionResult: 变量执行结果（包含状态、值、耗时、错误信息等）
        """
        start_time = time.time()
        
        # 获取模板信息（如果存在）
        template_id = getattr(self.context, 'template_id', None)
        template_path = getattr(self.context, 'template_path', None)
        
        # 记录开始执行日志
        execution_logger.info(
            self.context.task_id,
            f"Starting execution of variable '{self.variable_name}'",
            variable_name=self.variable_name,
            context={"source": self.metadata.source.value},
            template_id=template_id,
            template_path=template_path
        )
        
        try:
            # 第一步：检查任务是否在开始前被取消
            if self.context.is_task_cancelled():
                execution_logger.warning(
                    self.context.task_id,
                    f"Task cancelled before executing variable '{self.variable_name}'",
                    variable_name=self.variable_name,
                    template_id=template_id,
                    template_path=template_path
                )
                raise TaskCancelledException(self.context.task_id, f"Task cancelled before executing variable '{self.variable_name}'")
            
            # 第二步：检查依赖变量是否已就绪
            # 如果依赖的变量还未执行，则返回失败状态
            ready, missing = self.context.check_dependencies_ready(self.variable_name)
            if not ready:
                execution_logger.warning(
                    self.context.task_id,
                    f"Variable '{self.variable_name}' missing dependencies: {', '.join(missing)}",
                    variable_name=self.variable_name,
                    context={"missing_dependencies": missing},
                    template_id=template_id,
                    template_path=template_path
                )
                return VariableExecutionResult(
                    variable_name=self.variable_name,
                    status=VariableStatus.FAILED,
                    error=f"Missing dependencies: {', '.join(missing)}"
                )
            
            # 第三步：执行具体的变量逻辑（由子类实现）
            value = await self._execute_impl()
            
            # 第四步：检查任务是否在执行过程中被取消
            if self.context.is_task_cancelled():
                execution_logger.warning(
                    self.context.task_id,
                    f"Task cancelled while executing variable '{self.variable_name}'",
                    variable_name=self.variable_name,
                    template_id=template_id,
                    template_path=template_path
                )
                raise TaskCancelledException(self.context.task_id, f"Task cancelled while executing variable '{self.variable_name}'")
            
            # 第五步：将执行结果存入上下文，供其他依赖此变量的变量使用
            self.context.set_variable(self.variable_name, value)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录成功执行日志
            execution_logger.info(
                self.context.task_id,
                f"Successfully executed variable '{self.variable_name}' in {duration_ms}ms",
                variable_name=self.variable_name,
                context={
                    "duration_ms": duration_ms,
                    "result_type": type(value).__name__
                },
                template_id=template_id,
                template_path=template_path
            )
            
            # 返回成功的执行结果
            return VariableExecutionResult(
                variable_name=self.variable_name,
                status=VariableStatus.SUCCESS,
                value=value,
                duration_ms=duration_ms
            )
        
        except TaskCancelledException:
            # 任务被取消：返回失败结果，不使用默认值
            duration_ms = int((time.time() - start_time) * 1000)
            execution_logger.warning(
                self.context.task_id,
                f"Variable '{self.variable_name}' execution cancelled",
                variable_name=self.variable_name,
                context={"duration_ms": duration_ms},
                template_id=template_id,
                template_path=template_path
            )
            return VariableExecutionResult(
                variable_name=self.variable_name,
                status=VariableStatus.FAILED,
                error="Task was cancelled",
                duration_ms=duration_ms
            )
            
        except Exception as e:
            # 执行失败：尝试使用默认值或返回失败结果
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录错误日志
            execution_logger.error(
                self.context.task_id,
                f"Variable '{self.variable_name}' execution failed: {str(e)}",
                variable_name=self.variable_name,
                context={
                    "duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                template_id=template_id,
                template_path=template_path
            )
            
            # 如果配置了默认值，使用默认值作为回退
            # 这样可以保证模板渲染继续进行，而不是完全失败
            if self.metadata.default is not None:
                execution_logger.info(
                    self.context.task_id,
                    f"Using default value for variable '{self.variable_name}' after error",
                    variable_name=self.variable_name,
                    context={"default_value": str(self.metadata.default)},
                    template_id=template_id,
                    template_path=template_path
                )
                self.context.set_variable(self.variable_name, self.metadata.default)
                return VariableExecutionResult(
                    variable_name=self.variable_name,
                    status=VariableStatus.SUCCESS,
                    value=self.metadata.default,
                    duration_ms=duration_ms,
                    metadata={"used_default": True, "error": str(e)}
                )
            
            # 没有默认值，返回失败结果
            return VariableExecutionResult(
                variable_name=self.variable_name,
                status=VariableStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms
            )
    
    @abstractmethod
    async def _execute_impl(self) -> Any:
        """
        执行变量的具体逻辑（由子类实现）
        
        每种类型的执行器都需要实现这个方法：
        - SqlExecutor: 执行SQL查询
        - AiExecutor: 调用AI模型生成内容
        - ApiExecutor: 调用外部API
        - UserInputExecutor: 从用户输入获取值
        - SystemExecutor: 执行系统函数
        
        Returns:
            Any: 变量的值（类型根据变量类型而定）
            
        Raises:
            Exception: 执行失败时抛出异常（会被execute()方法捕获）
        """
        pass

