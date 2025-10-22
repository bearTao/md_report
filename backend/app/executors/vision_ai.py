"""Vision AI Executor - 视觉AI变量执行器"""

from typing import Any, List, Dict
from app.executors.base import BaseVariableExecutor
from app.core.exceptions import VisionAiExecutionError
import logging

logger = logging.getLogger(__name__)


class VisionAiExecutor(BaseVariableExecutor):
    """
    视觉AI执行器
    使用视觉大模型（如GPT-4V, GPT-4o）分析图片并生成文字描述
    """
    
    def __init__(self, *args, openai_api_key: str = None, openai_api_base: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base
    
    async def _execute_impl(self) -> Any:
        """
        执行视觉AI分析
        
        Returns:
            分析结果文本
        """
        try:
            # 获取vision_ai_config
            vision_config = self.metadata.vision_ai_config
            if not vision_config:
                raise VisionAiExecutionError(
                    self.variable_name,
                    "Missing vision_ai_config in variable metadata"
                )
            
            # 1. 获取图片数据（从依赖变量）
            image_source = vision_config.image_source
            if not self.context.has_variable(image_source):
                raise VisionAiExecutionError(
                    self.variable_name,
                    f"Image source variable '{image_source}' not found in context"
                )
            
            image_data = self.context.get_variable(image_source)
            logger.info(f"[{self.variable_name}] Got image data from: {image_source}")
            logger.info(f"[{self.variable_name}] Image data type: {type(image_data)}, preview: {str(image_data)[:200]}")
            
            # 2. 提取图片URL
            image_urls = self._extract_image_urls(image_data)
            if not image_urls:
                raise VisionAiExecutionError(
                    self.variable_name,
                    f"No valid image URLs found in '{image_source}'"
                )
            
            logger.info(f"[{self.variable_name}] Extracted {len(image_urls)} image URL(s)")
            logger.info(f"[{self.variable_name}] Image URLs: {image_urls}")
            
            # 3. 插值提示词模板
            prompt_text = self.context.interpolate_string(vision_config.prompt_template)
            logger.debug(f"[{self.variable_name}] Prompt: {prompt_text[:100]}...")
            
            # 4. 调用视觉模型
            from langchain_openai import ChatOpenAI
            from langchain.schema.messages import HumanMessage
            
            # 初始化模型
            llm = ChatOpenAI(
                model=vision_config.model,
                temperature=vision_config.temperature or 0.7,
                max_tokens=vision_config.max_tokens or 500,
                openai_api_key=self.openai_api_key,
                openai_api_base=self.openai_api_base
            )
            
            # 构建消息内容
            message_content = []
            
            # 添加文本部分
            message_content.append({
                "type": "text",
                "text": prompt_text
            })
            
            # 添加图片部分（支持多张图片）
            for image_url in image_urls:
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": "auto"  # auto/low/high
                    }
                })
            
            # 创建消息
            messages = [HumanMessage(content=message_content)]
            
            # 如果有system_prompt，添加系统消息
            if vision_config.system_prompt:
                from langchain.schema.messages import SystemMessage
                system_msg = SystemMessage(content=vision_config.system_prompt)
                messages = [system_msg] + messages
            
            logger.info(f"[{self.variable_name}] Calling vision model: {vision_config.model}")
            
            # 调用模型
            response = await llm.ainvoke(messages)
            
            # 提取结果
            result = response.content
            logger.info(f"[{self.variable_name}] Vision AI completed: {len(result)} chars")
            
            return result
            
        except VisionAiExecutionError:
            raise
        except Exception as e:
            logger.error(f"[{self.variable_name}] Vision AI execution failed: {str(e)}")
            raise VisionAiExecutionError(
                self.variable_name,
                f"Failed to analyze image: {str(e)}",
                original_error=e
            )
    
    def _extract_image_urls(self, image_data: Any) -> List[str]:
        """
        从图片变量中提取URL
        
        支持多种数据格式：
        1. 字符串URL: "https://..."
        2. Data URI: "data:image/png;base64,..."
        3. ImageExecutor返回: {"data": "...", "url": "...", "mime_type": "..."}
        4. 列表: [image1, image2, ...]
        
        Args:
            image_data: 图片数据
            
        Returns:
            图片URL列表
        """
        urls = []
        
        if isinstance(image_data, str):
            # 字符串：直接URL或Data URI
            if image_data.startswith(("http://", "https://", "data:")):
                urls.append(image_data)
        
        elif isinstance(image_data, dict):
            # 字典：ImageExecutor返回的格式
            if "data" in image_data:
                data = image_data["data"]
                
                # 检查data字段的内容类型
                if isinstance(data, str):
                    # 如果是URL字符串（http/https开头）或已经是data URI，直接使用
                    if data.startswith(("http://", "https://", "data:")):
                        urls.append(data)
                    # 如果是base64字符串且有mime_type，构建data URI
                    elif image_data.get("mime_type"):
                        mime_type = image_data["mime_type"]
                        urls.append(f"data:{mime_type};base64,{data}")
                
                # 如果是bytes，编码为base64
                elif isinstance(data, bytes) and image_data.get("mime_type"):
                    import base64
                    mime_type = image_data["mime_type"]
                    b64_data = base64.b64encode(data).decode('utf-8')
                    urls.append(f"data:{mime_type};base64,{b64_data}")
            
            # 兜底：如果上面没有提取到，尝试从url字段提取
            elif "url" in image_data:
                urls.append(image_data["url"])
            
            # 再次兜底：从markdown提取
            elif "markdown" in image_data:
                import re
                match = re.search(r'!\[.*?\]\((.*?)\)', image_data["markdown"])
                if match:
                    urls.append(match.group(1))
        
        elif isinstance(image_data, list):
            # 列表：递归处理每个元素
            for item in image_data:
                urls.extend(self._extract_image_urls(item))
        
        return urls

