"""
API变量执行器模块

功能说明：
- 调用外部RESTful API
- 支持变量插值（URL、参数、请求体）
- 支持重试机制
- 灵活的响应数据映射
"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.connectors.api import api_connector
from app.core.exceptions import ApiExecutionError


class ApiExecutor(BaseVariableExecutor):
    """
    API执行器
    
    功能：
    1. 调用外部HTTP/HTTPS API
    2. 支持所有HTTP方法（GET、POST、PUT、DELETE等）
    3. 自动重试失败的请求
    4. 灵活的响应数据提取和映射
    
    支持的响应映射模式：
    - None或{}: 返回完整的API响应
    - 字符串路径: 使用JMESPath提取单个字段（如："data.user.name"）
    - 字典映射: 提取多个字段并重命名（如：{"userName": "data.user.name"}）
    """
    
    async def _execute_impl(self) -> Any:
        """
        调用外部API并返回映射后的响应
        
        执行流程：
        1. 插值API配置（URL、参数、请求体）
        2. 发起HTTP请求（支持重试）
        3. 根据response_mapping模式处理响应
        
        响应映射模式：
        1. None或{}: 返回完整API响应
        2. 字符串: 使用JMESPath提取单个路径（可返回任意类型）
        3. 字典: 映射多个字段到新对象
        
        Returns:
            Any: 根据映射模式返回不同格式的数据
        """
        if not self.metadata.api_config:
            raise ApiExecutionError(
                self.variable_name,
                "api_config not provided"
            )
        
        config = self.metadata.api_config
        
        # 步骤1：插值API端点URL
        # 例如：https://api.com/users/{{user_id}} -> https://api.com/users/123
        try:
            url = self.context.interpolate_string(config.endpoint)
        except Exception as e:
            raise ApiExecutionError(
                self.variable_name,
                f"Failed to interpolate API endpoint: {str(e)}",
                e
            )
        
        # 步骤2：插值请求头、查询参数和请求体
        try:
            headers = self.context.interpolate_dict(config.headers or {})
            params = self.context.interpolate_dict(config.parameters or {})
            body = self.context.interpolate_dict(config.body or {}) if config.body else None
        except Exception as e:
            raise ApiExecutionError(
                self.variable_name,
                f"Failed to interpolate API config: {str(e)}",
                e
            )
        
        # 步骤3：发起API请求（支持自动重试）
        try:
            response = await api_connector.request(
                method=config.method,  # HTTP方法：GET、POST等
                url=url,  # 完整URL
                headers=headers,  # 请求头（如：Authorization）
                params=params,  # 查询参数（?key=value）
                json_data=body,  # 请求体（JSON格式）
                timeout=config.timeout or 10,  # 超时时间（秒）
                retry_count=config.retry_count or 0,  # 重试次数
                retry_status_codes=config.retry_status_codes,  # 哪些状态码需要重试
                retry_backoff=config.retry_backoff or 1.0  # 重试间隔（秒）
            )
        except Exception as e:
            raise ApiExecutionError(
                self.variable_name,
                f"API call failed: {str(e)}",
                e
            )
        
        # 步骤4：根据response_mapping类型处理响应
        mapping = config.response_mapping
        
        # 模式1：无映射或空字典 - 返回完整响应
        if mapping is None or (isinstance(mapping, dict) and not mapping):
            return response
        
        # 模式2：字符串路径 - 使用JMESPath提取单个路径
        # 示例：mapping="data.items[0].name" 提取第一个项目的名称
        if isinstance(mapping, str):
            try:
                extracted = api_connector._extract_path(response, mapping)
                return extracted
            except Exception as e:
                raise ApiExecutionError(
                    self.variable_name,
                    f"Failed to extract path '{mapping}': {str(e)}",
                    e
                )
        
        # 模式3：字典映射 - 提取多个字段并重命名
        # 示例：{"userId": "data.user.id", "userName": "data.user.name"}
        if isinstance(mapping, dict):
            try:
                mapped_data = api_connector.map_response(response, mapping)
                return mapped_data
            except Exception as e:
                raise ApiExecutionError(
                    self.variable_name,
                    f"Failed to map response: {str(e)}",
                    e
                )
        
        # 回退：返回原始响应
        return response

