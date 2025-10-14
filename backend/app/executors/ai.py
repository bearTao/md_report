"""AI generation executor - P0 with LangChain integration"""
from typing import Any, Dict
import json
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
    
    def __init__(self, *args, openai_api_key: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_api_key = openai_api_key
        
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
            llm = ChatOpenAI(
                model=config.model,
                temperature=config.temperature or 0.7,
                max_tokens=config.max_tokens or 2000,
                api_key=self.openai_api_key
            )
            
            # 2. Create output parser
            parser = JsonOutputParser()
            
            # 3. Add schema instructions to prompt if schema is provided
            if self.metadata.schema:
                schema_str = json.dumps(self.metadata.schema, indent=2, ensure_ascii=False)
                full_prompt = f"""{prompt_text}

请以JSON格式返回结果，遵循以下schema：
{schema_str}

只返回JSON，不要包含其他文字说明。"""
            else:
                full_prompt = f"""{prompt_text}

请以JSON格式返回结果。"""
            
            # 4. Create prompt template
            prompt = ChatPromptTemplate.from_template(full_prompt)
            
            # 5. Create chain: prompt | llm | parser
            chain = prompt | llm | parser
            
            # 6. Invoke chain
            result = await chain.ainvoke({})
            
            # 7. Validate against schema if provided
            if self.metadata.schema:
                self._validate_schema(result, self.metadata.schema)
            
            return result
            
        except Exception as e:
            raise AiGenerationError(
                self.variable_name,
                f"AI generation failed: {str(e)}",
                e
            )
    
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

