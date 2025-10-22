"""Image API Connector - 图片API连接器"""

import httpx
import base64
from typing import Dict, Any, Optional, Literal, List
import logging

logger = logging.getLogger(__name__)


class ImageApiConnector:
    """
    图片API连接器
    负责从HTTP/HTTPS API获取图片并转换为所需格式
    """
    
    def __init__(self, timeout: int = 30):
        """
        初始化图片API连接器
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
    
    async def fetch_image(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        output_format: Literal["base64", "url", "bytes"] = "base64",
        include_mime: bool = True
    ) -> Dict[str, Any]:
        """
        获取单张图片
        
        Args:
            url: 图片URL或API端点
            headers: 请求头（如认证信息）
            params: URL参数
            output_format: 输出格式 (base64/url/bytes)
            include_mime: 是否包含MIME类型
            
        Returns:
            {
                "data": "base64字符串或url或bytes",
                "mime_type": "image/png",
                "size": 12345,
                "url": "原始URL",
                "markdown": "![图片](data:image/png;base64,...)"
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Fetching image from: {url}")
                
                response = await client.get(
                    url,
                    headers=headers or {},
                    params=params or {},
                    follow_redirects=True
                )
                
                # 检查响应状态
                response.raise_for_status()
                
                # 获取内容
                content = response.content
                content_type = response.headers.get("content-type", "")
                
                # 验证是否为图片
                if not content_type.startswith("image/"):
                    logger.warning(f"Content-Type is not image: {content_type}")
                    # 尝试从URL推断
                    if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                        ext = url.lower().split('.')[-1]
                        content_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
                    else:
                        content_type = "image/png"  # 默认
                
                # 提取MIME类型
                mime_type = content_type.split(';')[0].strip()
                
                # 构建结果
                result = {
                    "url": url,
                    "mime_type": mime_type if include_mime else None,
                    "size": len(content)
                }
                
                if output_format == "base64":
                    # Base64编码
                    b64_data = base64.b64encode(content).decode('utf-8')
                    result["data"] = b64_data
                    # 生成Markdown格式
                    result["markdown"] = f"![图片](data:{mime_type};base64,{b64_data})"
                    
                elif output_format == "url":
                    # 返回原始URL
                    result["data"] = url
                    result["markdown"] = f"![图片]({url})"
                    
                elif output_format == "bytes":
                    # 返回字节数据（注意：JSON序列化时需要特殊处理）
                    result["data"] = content
                    result["markdown"] = None
                
                logger.info(f"Image fetched successfully: {len(content)} bytes")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching image: {e.response.status_code} - {url}")
            raise Exception(f"Failed to fetch image: HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching image: {url}")
            raise Exception(f"Timeout fetching image from {url}")
        except Exception as e:
            logger.error(f"Error fetching image: {str(e)}")
            raise Exception(f"Failed to fetch image: {str(e)}")
    
    async def fetch_multiple_images(
        self,
        urls: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量获取多张图片
        
        Args:
            urls: 图片URL列表
            **kwargs: 传递给fetch_image的其他参数
            
        Returns:
            图片数据列表
        """
        results = []
        for url in urls:
            try:
                result = await self.fetch_image(url, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to fetch image {url}: {str(e)}")
                # 添加错误占位符
                results.append({
                    "url": url,
                    "error": str(e),
                    "data": None,
                    "markdown": f"![图片加载失败]({url})"
                })
        
        return results


# 全局实例
image_api_connector = ImageApiConnector()

