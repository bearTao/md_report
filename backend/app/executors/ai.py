"""AI generation executor - P0 with LangChain integration"""
from typing import Any, Dict
import json
import re
from app.executors.base import BaseVariableExecutor
from app.core.exceptions import AiGenerationError

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI


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
        if not self.metadata.ai_config:
            raise AiGenerationError(
                self.variable_name,
                "ai_config not provided"
            )
        
        if not self.openai_api_key:
            raise AiGenerationError(
                self.variable_name,
                "OpenAI API key not configured"
            )
        
        config = self.metadata.ai_config
        
        # Interpolate prompt template with dependencies
        try:
            prompt_text = self.context.interpolate_string(config.prompt_template)
        except Exception as e:
            raise AiGenerationError(
                self.variable_name,
                f"Failed to interpolate prompt: {str(e)}",
                e
            )
        
        # Build LangChain components
        try:
            # 1. Create LLM
            llm_kwargs = {
                "model": config.model,
                "temperature": config.temperature or 0.7,
                "max_tokens": config.max_tokens or 2000,
                "api_key": self.openai_api_key
            }
            
            # 添加自定义API base（如硅基流动）
            if self.openai_api_base:
                llm_kwargs["base_url"] = self.openai_api_base
            
            llm = ChatOpenAI(**llm_kwargs)
            
            # 2. Create output parser with custom preprocessing
            parser = JsonOutputParser()
            
            # 3. Add schema instructions to prompt if schema is provided
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
            
            # 4. Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个专业的数据分析助手，擅长生成结构化的JSON数据。请直接返回纯JSON格式，不要使用markdown代码块（不要使用```json```），不要添加任何解释性文字。"),
                ("human", full_prompt)
            ])
            
            # 5. Create chain: prompt | llm
            chain = prompt | llm
            
            # 6. Invoke chain and get raw output
            raw_output = await chain.ainvoke({})
            
            # 7. Extract content from response
            if hasattr(raw_output, 'content'):
                content = raw_output.content
            else:
                content = str(raw_output)
            
            # Debug: Check if content is empty
            if not content or not content.strip():
                raise AiGenerationError(
                    self.variable_name,
                    f"AI returned empty response. Raw output type: {type(raw_output)}, Raw output: {raw_output}"
                )
            
            # 8. Clean and parse JSON output
            result = self._parse_ai_output(content)
            
            # 8. Validate against schema if provided
            if self.metadata.schema:
                self._validate_schema(result, self.metadata.schema)
            
            return result
            
        except Exception as e:
            raise AiGenerationError(
                self.variable_name,
                f"AI generation failed: {str(e)}",
                e
            )
    
    def _parse_ai_output(self, raw_output: str) -> Any:
        """
        解析AI输出，处理常见的格式问题
        """
        # 1. 去除Markdown代码块标记
        cleaned = raw_output.strip()
        
        # 匹配 ```json ... ``` 或 ``` ... ```
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(code_block_pattern, cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        
        # 2. 尝试解析JSON
        try:
            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError as e:
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

