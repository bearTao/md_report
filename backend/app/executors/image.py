"""Image Executor - 图片变量执行器"""

from typing import Any, Dict
from app.executors.base import BaseVariableExecutor
from app.connectors.image_api import image_api_connector
from app.core.exceptions import ImageExecutionError
import logging

logger = logging.getLogger(__name__)


class ImageExecutor(BaseVariableExecutor):
    """
    图片执行器
    从HTTP API获取图片并转换为所需格式
    """
    
    async def _execute_impl(self) -> Any:
        """
        执行图片获取
        
        Returns:
            单张图片: {data, mime_type, size, url, markdown}
            多张图片: [{data, ...}, {data, ...}, ...]
        """
        try:
            # 获取image_config
            image_config = self.metadata.image_config
            if not image_config:
                raise ImageExecutionError(
                    self.variable_name,
                    "Missing image_config in variable metadata"
                )
            
            # 插值API端点
            endpoint = self.context.interpolate_string(image_config.endpoint)
            logger.info(f"[{self.variable_name}] Fetching image from: {endpoint}")
            
            # 插值headers
            headers = {}
            if image_config.headers:
                for key, value in image_config.headers.items():
                    headers[key] = self.context.interpolate_string(value)
            
            # 插值parameters
            params = {}
            if image_config.parameters:
                for key, value in image_config.parameters.items():
                    if isinstance(value, str):
                        params[key] = self.context.interpolate_string(value)
                    else:
                        params[key] = value
            
            # 判断是单张还是多张
            if image_config.multiple:
                # 多张图片
                # endpoint应该返回一个URL列表，或者是一个API返回多个图片URL
                # 简化处理：假设endpoint本身是一个数组（需要从context获取）
                urls = []
                
                # 尝试解析endpoint是否包含数组变量
                # 如果endpoint包含变量插值结果是列表，则使用该列表
                try:
                    # 如果endpoint本身就是多个URL的数组变量引用
                    # 例如: {{image_urls}}
                    import re
                    var_match = re.search(r'\{\{([^}]+)\}\}', image_config.endpoint)
                    if var_match:
                        var_name = var_match.group(1).strip()
                        var_value = self.context.get_variable(var_name)
                        if isinstance(var_value, list):
                            urls = var_value
                        else:
                            urls = [endpoint]
                    else:
                        urls = [endpoint]
                except:
                    urls = [endpoint]
                
                # 批量获取
                result = await image_api_connector.fetch_multiple_images(
                    urls=urls,
                    headers=headers,
                    params=params,
                    output_format=image_config.output_format,
                    include_mime=True
                )
                
                logger.info(f"[{self.variable_name}] Fetched {len(result)} images")
                return result
                
            else:
                # 单张图片
                result = await image_api_connector.fetch_image(
                    url=endpoint,
                    headers=headers,
                    params=params,
                    output_format=image_config.output_format,
                    include_mime=True
                )
                
                logger.info(f"[{self.variable_name}] Fetched image: {result['size']} bytes")
                return result
                
        except ImageExecutionError:
            raise
        except Exception as e:
            logger.error(f"[{self.variable_name}] Image execution failed: {str(e)}")
            raise ImageExecutionError(
                self.variable_name,
                f"Failed to fetch image: {str(e)}",
                original_error=e
            )

