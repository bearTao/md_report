"""AI generation executor - P0 with LangChain integration"""
from typing import Any, Dict
import json
import re
import logging
from app.executors.base import BaseVariableExecutor
from app.core.exceptions import AiGenerationError

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.schema.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class AiExecutor(BaseVariableExecutor):
    """
    Executes AI generation type variables
    Uses LangChain for structured output
    """
    
    def __init__(self, *args, openai_api_key: str = None, openai_api_base: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base
        
    async def _execute_impl(self) -> Any:
        """
        Generate AI content using LangChain
        """
        logger.info(f"🤖 开始执行AI变量: {self.variable_name}")
        
        if not self.metadata.ai_config:
            logger.error(f"❌ 变量 {self.variable_name} 缺少 ai_config")
            raise AiGenerationError(
                self.variable_name,
                "ai_config not provided"
            )
        
        if not self.openai_api_key:
            logger.error(f"❌ OpenAI API key 未配置")
            raise AiGenerationError(
                self.variable_name,
                "OpenAI API key not configured"
            )
        
        config = self.metadata.ai_config
        logger.info(f"📝 AI配置: model={config.model}, temperature={config.temperature}")
        
        # Render prompt template with Jinja2 (supports full syntax)
        try:
            logger.debug(f"🔄 开始渲染提示词模板")
            logger.debug(f"提示词模板:\n{config.prompt_template}")
            logger.debug(f"依赖变量: {self.metadata.dependencies}")
            
            # 显示依赖变量的值
            if self.metadata.dependencies:
                for dep in self.metadata.dependencies:
                    dep_value = self.context.get_variable(dep)
                    logger.debug(f"依赖变量 '{dep}' 的值: {str(dep_value)[:200]}...")
            
            # 使用 Jinja2 渲染 prompt_template（支持完整语法：循环、条件、过滤器等）
            from app.services.renderer import template_renderer
            prompt_text = template_renderer.render(
                config.prompt_template, 
                self.context.get_all_variables()
            )
            logger.debug(f"✅ 提示词渲染成功，长度: {len(prompt_text)} 字符")
            logger.info(f"📝 最终提示词预览:\n{'-'*60}\n{prompt_text[:500]}...\n{'-'*60}")
        except Exception as e:
            logger.error(f"❌ 提示词渲染失败: {str(e)}", exc_info=True)
            raise AiGenerationError(
                self.variable_name,
                f"Failed to render prompt template: {str(e)}",
                e
            )
        
        # Build LangChain components
        try:
            # 1. Create LLM
            logger.info(f"🔧 创建LLM实例...")
            llm_kwargs = {
                "model": config.model,
                "temperature": config.temperature or 0.7,
                "max_tokens": config.max_tokens or 2000,
                "api_key": self.openai_api_key
            }
            
            # 添加自定义API base（如硅基流动）
            if self.openai_api_base:
                llm_kwargs["base_url"] = self.openai_api_base
                logger.info(f"🌐 使用自定义API base: {self.openai_api_base}")
            
            # 隐藏API key的配置信息
            safe_config = {k: (v if k != "api_key" else "***") for k, v in llm_kwargs.items()}
            logger.debug(f"LLM配置: {safe_config}")
            llm = ChatOpenAI(**llm_kwargs)
            logger.info(f"✅ LLM实例创建成功")
            
            # 2. Add schema instructions to prompt if schema is provided
            if self.metadata.schema:
                # 生成简化的schema描述，避免JSON格式被Jinja2解析
                schema_desc = self._generate_schema_description(self.metadata.schema)
                full_prompt = f"""{prompt_text}

请以JSON格式返回结果，{schema_desc}

重要提示：
1. 必须返回完整的JSON，不能中断
2. 确保每个字段后面有逗号（最后一个字段除外）
3. 确保所有字符串都用双引号包裹
4. 不要使用markdown代码块

只返回JSON，不要包含其他文字说明。"""
            else:
                full_prompt = f"""{prompt_text}

请以JSON格式返回结果。确保JSON格式完全正确，每个字段后都有逗号（最后一个除外）。"""
            
            # 4. Create messages directly (avoid ChatPromptTemplate variable interpolation)
            messages = [
                SystemMessage(content="你是一个专业的数据分析助手，擅长生成结构化的JSON数据。请直接返回纯JSON格式，不要使用markdown代码块（不要使用```json```），不要添加任何解释性文字。"),
                HumanMessage(content=full_prompt)
            ]
            
            # 5. Invoke LLM directly with messages
            logger.info(f"🚀 调用AI模型生成内容...")
            logger.info(f"⏳ 请等待AI响应（可能需要10-60秒）...")
            logger.debug(f"消息数量: {len(messages)}")
            
            import time
            import asyncio
            start_time = time.time()
            
            try:
                # 设置超时时间：120秒（2分钟）
                raw_output = await asyncio.wait_for(
                    llm.ainvoke(messages),
                    timeout=120.0
                )
                elapsed = time.time() - start_time
                
                logger.info(f"✅ AI响应完成，耗时: {elapsed:.2f}秒")
                logger.debug(f"响应对象类型: {type(raw_output)}")
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.error(f"❌ AI API调用超时（120秒），耗时: {elapsed:.2f}秒")
                raise AiGenerationError(
                    self.variable_name,
                    f"AI API call timed out after 120 seconds"
                )
            except Exception as api_error:
                elapsed = time.time() - start_time
                logger.error(f"❌ AI API调用失败，耗时: {elapsed:.2f}秒")
                logger.error(f"错误类型: {type(api_error).__name__}")
                logger.error(f"错误详情: {str(api_error)}", exc_info=True)
                raise
            
            # 7. Extract content from response
            if hasattr(raw_output, 'content'):
                content = raw_output.content
                logger.debug(f"从响应的content属性提取内容")
            else:
                content = str(raw_output)
                logger.debug(f"直接转换响应为字符串")
            
            logger.info(f"📄 AI响应内容长度: {len(content)} 字符")
            logger.debug(f"AI完整响应:\n{'-'*60}\n{content}\n{'-'*60}")
            
            # Debug: Check if content is empty
            if not content or not content.strip():
                raise AiGenerationError(
                    self.variable_name,
                    f"AI returned empty response. Raw output type: {type(raw_output)}, Raw output: {raw_output}"
                )
            
            # 8. Clean and parse JSON output
            logger.info(f"🔍 解析AI输出为JSON...")
            result = self._parse_ai_output(content)
            logger.info(f"✅ JSON解析成功")
            logger.debug(f"解析结果: {str(result)[:200]}...")
            
            # 9. Validate against schema if provided
            if self.metadata.schema:
                logger.info(f"🔍 验证schema...")
                self._validate_schema(result, self.metadata.schema)
                logger.info(f"✅ Schema验证通过")
            
            logger.info(f"🎉 AI变量 {self.variable_name} 执行成功")
            return result
            
        except Exception as e:
            logger.error(f"❌ AI生成失败: {str(e)}", exc_info=True)
            raise AiGenerationError(
                self.variable_name,
                f"AI generation failed: {str(e)}",
                e
            )
    
    def _parse_ai_output(self, raw_output: str) -> Any:
        """
        解析AI输出，处理常见的格式问题
        """
        logger.debug(f"开始解析AI输出，原始长度: {len(raw_output)} 字符")
        
        # 1. 去除Markdown代码块标记
        cleaned = raw_output.strip()
        logger.debug(f"去除首尾空白后长度: {len(cleaned)} 字符")
        
        # 匹配 ```json ... ``` 或 ``` ... ```
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(code_block_pattern, cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
            logger.debug(f"检测到Markdown代码块，提取后长度: {len(cleaned)} 字符")
        
        # 2. 尝试解析JSON
        logger.debug(f"尝试解析JSON:\n{cleaned[:500]}...")
        try:
            result = json.loads(cleaned)
            logger.debug(f"✅ JSON解析成功，结果类型: {type(result)}")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  初次JSON解析失败: {str(e)}")
            logger.debug(f"解析失败位置: 行{e.lineno} 列{e.colno}")
            # 3. 如果失败，尝试修复常见错误
            fixed = cleaned
            
            # 修复1: 对象之间缺少逗号 }\n  {
            fixed = re.sub(r'\}\s*\n\s*\{', '},\n  {', fixed)
            
            # 修复2: 数组元素之间缺少逗号 ]\n  [
            fixed = re.sub(r'\]\s*\n\s*\[', '],\n  [', fixed)
            
            # 修复3: 字符串值结束后缺少逗号
            # 匹配: "value"\n  "nextfield": 应该是 "value",\n  "nextfield":
            fixed = re.sub(r'"\s*\n\s+"([^"]+)"\s*:', r'",\n    "\1":', fixed)
            
            # 修复4: 数字/布尔值后缺少逗号
            # 匹配: 123\n  "nextfield": 应该是 123,\n  "nextfield":
            fixed = re.sub(r'(\d+|\btrue\b|\bfalse\b|\bnull\b)\s*\n\s+"([^"]+)"\s*:', r'\1,\n    "\2":', fixed)
            
            try:
                result = json.loads(fixed)
                return result
            except json.JSONDecodeError as parse_error:
                # 如果还是失败，抛出更详细的错误
                raise AiGenerationError(
                    self.variable_name,
                    f"Invalid JSON format. Original output (first 1000 chars):\n{raw_output[:1000]}\n\nParse error: {str(parse_error)}"
                )
    
    def _generate_schema_description(self, schema: Dict[str, Any]) -> str:
        """
        生成schema的文字描述，避免JSON格式问题
        """
        schema_type = schema.get("type", "object")
        
        if schema_type == "array":
            if "items" in schema:
                item_schema = schema["items"]
                if item_schema.get("type") == "object" and "properties" in item_schema:
                    props = item_schema["properties"]
                    required_fields = item_schema.get("required", [])
                    
                    fields_desc = []
                    for field_name, field_info in props.items():
                        field_type = field_info.get("type", "string")
                        is_required = "必需" if field_name in required_fields else "可选"
                        fields_desc.append(f"{field_name}({field_type}, {is_required})")
                    
                    return f"返回数组，每个元素是对象，包含字段: {', '.join(fields_desc)}"
                else:
                    item_type = item_schema.get("type", "any")
                    return f"返回{item_type}类型的数组"
            return "返回数组"
        
        elif schema_type == "object":
            if "properties" in schema:
                props = schema["properties"]
                required_fields = schema.get("required", [])
                
                fields_desc = []
                for field_name, field_info in props.items():
                    field_type = field_info.get("type", "string")
                    is_required = "必需" if field_name in required_fields else "可选"
                    
                    # 处理嵌套对象
                    if field_type == "object" and "properties" in field_info:
                        nested_props = field_info["properties"]
                        nested_fields = [f"{k}({v.get('type', 'string')})" for k, v in nested_props.items()]
                        fields_desc.append(f"{field_name}(对象包含: {', '.join(nested_fields)}, {is_required})")
                    elif field_type == "array":
                        fields_desc.append(f"{field_name}(数组, {is_required})")
                    else:
                        fields_desc.append(f"{field_name}({field_type}, {is_required})")
                
                return f"返回对象，包含字段: {', '.join(fields_desc)}"
            return "返回对象"
        
        return f"返回{schema_type}类型"
    
    def _validate_schema(self, data: Any, schema: Dict[str, Any]):
        """
        Basic schema validation
        """
        schema_type = schema.get("type")
        
        if schema_type == "array":
            if not isinstance(data, list):
                raise ValueError(f"Expected array, got {type(data).__name__}")
                
            # Validate array items if schema provided
            if "items" in schema and len(data) > 0:
                item_schema = schema["items"]
                for i, item in enumerate(data):
                    try:
                        self._validate_schema(item, item_schema)
                    except ValueError as e:
                        raise ValueError(f"Array item {i} validation failed: {str(e)}")
                        
        elif schema_type == "object":
            if not isinstance(data, dict):
                raise ValueError(f"Expected object, got {type(data).__name__}")
                
            # Validate required properties
            if "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    if prop_name in data:
                        self._validate_schema(data[prop_name], prop_schema)
                        
            # Check for required fields (basic)
            if "required" in schema:
                for required_field in schema["required"]:
                    if required_field not in data:
                        raise ValueError(f"Required field '{required_field}' missing")
                        
        elif schema_type == "string":
            if not isinstance(data, str):
                raise ValueError(f"Expected string, got {type(data).__name__}")
                
            # Check enum if provided
            if "enum" in schema and data not in schema["enum"]:
                raise ValueError(f"Value '{data}' not in allowed enum: {schema['enum']}")
                
        elif schema_type == "number":
            if not isinstance(data, (int, float)):
                raise ValueError(f"Expected number, got {type(data).__name__}")
                
        elif schema_type == "boolean":
            if not isinstance(data, bool):
                raise ValueError(f"Expected boolean, got {type(data).__name__}")

