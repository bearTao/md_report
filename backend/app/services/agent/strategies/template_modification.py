"""
模板修改执行策略

本模块实现模板修改操作的具体执行逻辑,包括:
- 添加新章节
- 修改现有章节
- 删除章节
- 数据需求分析
- Jinja2模板生成
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import os
import re

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from jinja2 import Template as Jinja2Template, TemplateSyntaxError

from app.core.agent_config import get_config
from app.services.agent.strategies.base import ExecutionStrategy
from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    TemplateModificationDetails,
    ConversationMemory,
    VariableInfo,
    VariableType,
    OperationType
)
from app.models.db_models import AIProviderKey

logger = logging.getLogger(__name__)


class TemplateModificationStrategy(ExecutionStrategy):
    """
    模板修改执行策略
    
    负责执行模板修改操作,包括:
    1. 分析模板结构
    2. 确定插入/修改位置
    3. 分析数据需求
    4. 生成Jinja2代码
    5. 更新临时模板
    
    Attributes:
        db: 数据库会话
        llm: LangChain LLM实例
    """
    
    def __init__(self, db: Session):
        """
        初始化模板修改策略
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.llm = None
        
        # 尝试初始化LLM
        try:
            # 从配置文件加载配置
            config = get_config()
            api_key, api_base = self._get_ai_config()
            
            if api_key:
                # 使用配置文件中的模板修改策略配置，如果没有则回退到意图解析器配置
                llm_config = config.intent_parser.llm  # 复用意图解析器的模型配置
                
                llm_kwargs = {
                    "model": llm_config.model,
                    "temperature": 0.3,  # 较低温度以获得更精确的模板代码
                    "api_key": api_key
                }
                if api_base:
                    llm_kwargs["base_url"] = api_base
                if llm_config.max_tokens:
                    llm_kwargs["max_tokens"] = llm_config.max_tokens
                if llm_config.timeout:
                    llm_kwargs["timeout"] = llm_config.timeout
                
                self.llm = ChatOpenAI(**llm_kwargs)
                logger.info(f"TemplateModificationStrategy LLM初始化成功 - model: {llm_config.model}")
            else:
                logger.warning("未找到OpenAI API密钥,模板修改功能将不可用")
        except Exception as e:
            logger.error(f"LLM初始化失败: {str(e)}")
    
    def _get_ai_config(self) -> tuple[Optional[str], Optional[str]]:
        """获取OpenAI API配置"""
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        if api_key:
            return api_key, api_base
        
        try:
            config = self.db.query(AIProviderKey).filter(
                AIProviderKey.provider == "openai"
            ).first()
            
            if config:
                return config.api_key_ciphertext, config.api_base
        except Exception as e:
            logger.warning(f"从数据库获取AI配置失败: {str(e)}")
        
        return None, None
    
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行模板修改操作
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Returns:
            Operation: 执行结果
        """
        start_time = datetime.now()
        cost_usd = 0.0
        
        try:
            # 检查LLM是否可用
            if not self.llm:
                raise ValueError("AI服务未初始化,无法执行模板修改")
            
            mod_map = {
                OperationType.ADD_SECTION: "add",
                OperationType.MODIFY_SECTION: "modify",
                OperationType.REMOVE_SECTION: "remove",
            }
            modification_type = step.parameters.get("modification_type") or mod_map.get(step.operation_type)
            
            # 处理字符串格式的操作类型 (add_section -> add)
            if modification_type in ["add_section", "modify_section", "remove_section"]:
                modification_type = modification_type.replace("_section", "")
            section_name_param = step.parameters.get("section_name", "")
            section_description = step.parameters.get("section_description", "")
            
            logger.info(
                f"执行模板修改: {modification_type}, "
                f"章节: {section_name_param or section_description[:50]}"
            )
            
            # 根据操作类型执行不同的逻辑
            if modification_type == "add":
                result_details, op_cost = await self._add_section(
                    section_description, memory, section_name_param
                )
                cost_usd += op_cost
            elif modification_type == "modify":
                # 为测试可控性，优先调用可mock的方法
                result_details, op_cost = await self._modify_existing_section(
                    section_name_param, section_description, memory
                )
                cost_usd += op_cost
            elif modification_type == "remove":
                result_details, op_cost = await self._remove_section(
                    section_name_param, memory
                )
                cost_usd += op_cost
            else:
                raise ValueError(f"未知的模板修改类型: {modification_type}")
            
            # 计算执行时长
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            logger.info(
                f"模板修改完成: {modification_type}, "
                f"耗时: {duration_ms}ms, 成本: ${cost_usd:.4f}"
            )
            
            return self._create_operation_result(
                operation_type=step.operation_type,
                details=result_details,
                success=True,
                duration_ms=duration_ms,
                cost_usd=cost_usd
            )
        
        except Exception as e:
            logger.error(f"模板修改失败: {str(e)}")
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 创建失败的操作结果
            safe_mod_type = (modification_type if isinstance(modification_type, str) and modification_type in ["add", "modify", "remove"] else "add")
            details = TemplateModificationDetails(
                modification_type=safe_mod_type,
                section_name=section_name_param,
                section_content=None,
                insertion_point=None,
                new_variables=[]
            )
            
            return self._create_operation_result(
                operation_type=step.operation_type,
                details=details,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
                cost_usd=cost_usd
            )
    
    async def _add_section(
        self,
        section_description: str,
        memory: ConversationMemory,
        section_name: Optional[str] = None
    ) -> tuple[TemplateModificationDetails, float]:
        """
        添加新章节
        
        Args:
            section_description: 章节描述
            memory: 对话记忆
        
        Returns:
            tuple: (操作详情, 成本)
        """
        # 步骤1: 确定插入位置
        insertion_point = await self._find_insertion_point(memory)
        
        # 步骤2: 分析数据需求
        data_requirements, cost1 = await self._analyze_data_requirements(
            section_description, memory
        )
        
        # 步骤3: 生成Jinja2模板
        section_content, generated_section_name, cost2 = await self._generate_section_jinja2(
            section_description, data_requirements, memory
        )
        
        # 步骤4: 创建运行时变量（传入section_content以提取依赖关系）
        new_variables = self._create_runtime_variables(
            data_requirements, memory, section_content
        )
        
        # 步骤5: 更新临时模板
        self._update_temporary_template(
            memory, section_content, insertion_point
        )
        
        # 确定最终章节名：优先使用显式传入的名称，其次是LLM生成的名称，最后使用描述
        final_section_name = section_name or generated_section_name or section_description
        details = TemplateModificationDetails(
            modification_type="add",
            section_name=final_section_name,
            section_content=section_content,
            insertion_point=insertion_point,
            new_variables=new_variables
        )
        
        return details, cost1 + cost2
    
    async def _modify_existing_section(
        self,
        section_name: str,
        modification_description: str,
        memory: ConversationMemory
    ) -> tuple[TemplateModificationDetails, float]:
        """
        修改现有章节
        
        Args:
            section_name: 章节名称
            modification_description: 修改描述
            memory: 对话记忆
        
        Returns:
            tuple: (操作详情, 成本)
        """
        import re
        cost_usd = 0.0
        
        # 获取当前模板内容
        template_content = memory.report_state.template_content
        
        # 查找章节（支持 # 或 ## 标题）
        section_pattern = rf'^(#+)\s+{re.escape(section_name)}\s*$'
        lines = template_content.split('\n')
        section_start = -1
        section_level = 0
        
        for i, line in enumerate(lines):
            match = re.match(section_pattern, line.strip())
            if match:
                section_start = i
                section_level = len(match.group(1))
                break
        
        if section_start == -1:
            logger.warning(f"未找到章节: {section_name}，将在末尾添加修改后的内容")
            # 如果找不到章节，使用添加章节的逻辑
            data_requirements = {
                "requirements": [],
                "description": modification_description
            }
            new_content, _, llm_cost = await self._generate_section_jinja2(
                modification_description, data_requirements, memory
            )
            cost_usd += llm_cost
            
            # 添加到末尾
            self._update_temporary_template(memory, new_content, "document_end")
            
            details = TemplateModificationDetails(
                modification_type="modify",
                section_name=section_name,
                section_content=new_content,
                insertion_point="document_end",
                new_variables=[]
            )
            return details, cost_usd
        
        # 找到章节结束位置（下一个同级或更高级标题）
        section_end = len(lines)
        for i in range(section_start + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith('#'):
                # 检查标题级别
                current_level = len(re.match(r'^(#+)', line).group(1))
                if current_level <= section_level:
                    section_end = i
                    break
        
        # 提取原章节内容
        old_section_content = '\n'.join(lines[section_start:section_end])
        
        # 使用LLM根据修改描述重新生成章节内容
        prompt = f"""请根据以下修改要求，重新生成章节内容。

原章节名称: {section_name}
原章节内容:
{old_section_content}

修改要求: {modification_description}

请生成修改后的完整章节内容（包括标题），使用Markdown格式。如果需要动态数据，请使用Jinja2语法 {{{{ variable_name }}}}。
"""
        
        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            new_section_content = response.content.strip()
            cost_usd += self._estimate_llm_cost(prompt, new_section_content)
        except Exception as e:
            logger.error(f"LLM生成章节失败: {str(e)}，使用原内容")
            new_section_content = old_section_content
        
        # 替换章节内容
        new_lines = lines[:section_start] + [new_section_content] + lines[section_end:]
        memory.report_state.template_content = '\n'.join(new_lines)
        
        logger.info(f"章节修改完成: {section_name}")
        
        details = TemplateModificationDetails(
            modification_type="modify",
            section_name=section_name,
            section_content=new_section_content,
            insertion_point=None,
            new_variables=[]
        )
        return details, cost_usd
    
    async def _remove_section(
        self,
        section_name: str,
        memory: ConversationMemory
    ) -> tuple[TemplateModificationDetails, float]:
        """
        删除章节
        
        Args:
            section_name: 章节名称
            memory: 对话记忆
        
        Returns:
            tuple: (操作详情, 成本)
        """
        import re
        
        # 获取当前模板内容
        template_content = memory.report_state.template_content
        
        # 查找章节（支持 # 或 ## 标题）
        section_pattern = rf'^(#+)\s+{re.escape(section_name)}\s*$'
        lines = template_content.split('\n')
        section_start = -1
        section_level = 0
        
        for i, line in enumerate(lines):
            match = re.match(section_pattern, line.strip())
            if match:
                section_start = i
                section_level = len(match.group(1))
                break
        
        if section_start == -1:
            logger.warning(f"未找到章节: {section_name}，无法删除")
            raise ValueError(f"章节不存在: {section_name}")
        
        # 找到章节结束位置（下一个同级或更高级标题）
        section_end = len(lines)
        for i in range(section_start + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith('#'):
                # 检查标题级别
                current_level = len(re.match(r'^(#+)', line).group(1))
                if current_level <= section_level:
                    section_end = i
                    break
        
        # 提取被删除的章节内容（用于记录）
        removed_content = '\n'.join(lines[section_start:section_end])
        
        # 删除章节
        new_lines = lines[:section_start] + lines[section_end:]
        memory.report_state.template_content = '\n'.join(new_lines)
        
        logger.info(f"章节删除完成: {section_name}")
        
        details = TemplateModificationDetails(
            modification_type="remove",
            section_name=section_name,
            section_content=removed_content,
            insertion_point=None,
            new_variables=[]
        )
        
        return details, 0.0
    
    async def _find_insertion_point(self, memory: ConversationMemory) -> str:
        """
        找到合适的插入位置
        
        Args:
            memory: 对话记忆
        
        Returns:
            str: 插入位置描述
        """
        # 简化实现: 默认插入到末尾
        return "document_end"
    
    async def _analyze_data_requirements(
        self,
        section_description: str,
        memory: ConversationMemory
    ) -> tuple[Dict[str, Any], float]:
        """
        分析数据需求
        
        使用LLM分析新章节需要哪些数据。
        
        Args:
            section_description: 章节描述
            memory: 对话记忆
        
        Returns:
            tuple: (数据需求字典, 成本)
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """你是一个数据需求分析专家。分析用户想要添加的报告章节,确定需要哪些数据。

**可用的数据源类型:**
- user_input: 用户直接提供的值
- sql: 从数据库查询
- api: 从外部API获取
- ai_generation: 使用AI生成内容
- system: 系统变量(如当前时间)
- constant: 常量值

**章节描述:**
{section_description}

**当前已有变量:**
{existing_variables}

请分析并返回JSON格式的数据需求列表,每个需求包含:
- variable_name: 变量名(小写下划线命名)
- source_type: 数据源类型
- description: 变量说明
- query: SQL查询或API URL(如果适用)

示例:
```json
{{
  "requirements": [
    {{
      "variable_name": "competitor_data",
      "source_type": "sql",
      "description": "竞争对手数据",
      "query": "SELECT * FROM competitors WHERE active = true"
    }},
    {{
      "variable_name": "market_analysis",
      "source_type": "ai_generation",
      "description": "市场分析内容",
      "query": null
    }}
  ]
}}
```

请直接返回JSON,不要包含其他内容。"""),
            ("user", "分析数据需求")
        ])
        
        try:
            existing_vars = list(memory.report_state.variables.keys())
            
            prompt = prompt_template.format_messages(
                section_description=section_description,
                existing_variables=", ".join(existing_vars) if existing_vars else "无"
            )
            
            response = await self.llm.ainvoke(prompt)
            
            # 解析JSON响应
            import json
            content = response.content.strip()
            # 移除可能的markdown代码块标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data_requirements = json.loads(content)
            
            # 估算成本
            cost = self._estimate_llm_cost(prompt[0].content + response.content)
            
            logger.info(f"数据需求分析完成: {len(data_requirements.get('requirements', []))} 个需求")
            return data_requirements, cost
        
        except Exception as e:
            logger.error(f"数据需求分析失败: {str(e)}")
            return {"requirements": []}, 0.0
    
    async def _generate_section_jinja2(
        self,
        section_description: str,
        data_requirements: Dict[str, Any],
        memory: ConversationMemory
    ) -> tuple[str, str, float]:
        """
        生成章节的Jinja2模板代码
        
        Args:
            section_description: 章节描述
            data_requirements: 数据需求
            memory: 对话记忆
        
        Returns:
            tuple: (Jinja2代码, 章节名称, 成本)
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """你是一个Jinja2模板代码生成专家。根据章节描述和数据需求,生成Markdown格式的Jinja2模板代码。

**要求:**
1. 使用Markdown语法
2. 使用Jinja2语法引用变量: {{ variable_name }}
3. 适当使用条件语句: {% if condition %}...{% endif %}
4. 适当使用循环: {% for item in items %}...{% endfor %}
5. 处理空值情况
6. 代码应该简洁、清晰、可维护
7. 包含合适的标题(使用##或###)

**章节描述:**
{section_description}

**可用变量:**
{variables}

**示例输出:**
```markdown
## 竞争对手分析

{% if competitor_data %}
### 主要竞争对手

{% for competitor in competitor_data %}
- **{{ competitor.name }}**: 市场份额 {{ competitor.market_share }}%
{% endfor %}
{% else %}
暂无竞争对手数据。
{% endif %}

### 市场趋势

{{ market_analysis }}
```

请生成Jinja2模板代码:"""),
            ("user", "生成模板")
        ])
        
        try:
            # 构建变量列表
            variables = []
            for req in data_requirements.get("requirements", []):
                variables.append(f"- {req['variable_name']}: {req['description']}")
            
            prompt = prompt_template.format_messages(
                section_description=section_description,
                variables="\n".join(variables) if variables else "无"
            )
            
            response = await self.llm.ainvoke(prompt)
            
            # 提取Jinja2代码
            content = response.content.strip()
            # 移除markdown代码块标记
            if "```markdown" in content:
                content = content.split("```markdown")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # 验证Jinja2语法
            try:
                Jinja2Template(content)
                logger.info("Jinja2模板语法验证通过")
            except TemplateSyntaxError as e:
                logger.warning(f"Jinja2语法错误: {str(e)},将使用简化版本")
                content = f"## {section_description}\n\n内容待生成"
            
            # 提取章节名称(第一个标题)
            section_name = "新章节"
            match = re.search(r'^##\s+(.+)$', content, re.MULTILINE)
            if match:
                section_name = match.group(1).strip()
            
            # 估算成本
            cost = self._estimate_llm_cost(prompt[0].content + response.content)
            
            logger.info(f"Jinja2模板生成完成: {section_name}")
            return content, section_name, cost
        
        except Exception as e:
            logger.error(f"Jinja2生成失败: {str(e)}")
            # 返回简单模板
            return f"## {section_description}\n\n内容待生成", section_description, 0.0
    
    def _create_runtime_variables(
        self,
        data_requirements: Dict[str, Any],
        memory: ConversationMemory,
        section_content: Optional[str] = None
    ) -> List[str]:
        """
        创建运行时变量
        
        Args:
            data_requirements: 数据需求
            memory: 对话记忆
            section_content: 章节Jinja2模板内容（用于提取依赖关系）
        
        Returns:
            List[str]: 创建的变量名列表
        """
        from jinja2 import Environment, meta
        
        new_variables = []
        
        # 从模板中提取所有变量依赖
        template_dependencies = set()
        if section_content:
            try:
                env = Environment()
                ast = env.parse(section_content)
                template_dependencies = meta.find_undeclared_variables(ast)
                logger.info(f"从模板中提取到依赖变量: {template_dependencies}")
            except Exception as e:
                logger.warning(f"提取模板依赖失败: {str(e)}")
        
        for req in data_requirements.get("requirements", []):
            var_name = req["variable_name"]
            
            # 确定此变量的依赖关系（从模板中使用的其他变量）
            dependencies = list(template_dependencies - {var_name})  # 排除自身
            # 只保留已存在的变量
            dependencies = [dep for dep in dependencies if dep in memory.report_state.variables]
            
            # 创建VariableInfo
            var_info = VariableInfo(
                name=var_name,
                value=None,  # 将在后续执行时填充
                source=req["source_type"],
                variable_type=VariableType.RUNTIME,
                metadata={
                    "description": req["description"],
                    "query": req.get("query"),
                    "dependencies": dependencies,  # 设置依赖关系
                    "created_by": "template_modification",
                    "created_at": datetime.now().isoformat()
                },
                last_updated=datetime.now()
            )
            
            # 添加到报告状态
            memory.report_state.variables[var_name] = var_info
            new_variables.append(var_name)
        
        logger.info(f"创建了 {len(new_variables)} 个运行时变量")
        return new_variables
    
    def _update_temporary_template(
        self,
        memory: ConversationMemory,
        section_content: str,
        insertion_point: str
    ) -> None:
        """
        更新临时模板
        
        Args:
            memory: 对话记忆
            section_content: 章节内容
            insertion_point: 插入位置
        """
        # 获取当前模板内容
        current_template = memory.report_state.template_content or ""
        
        base_content = current_template or ""
        if insertion_point == "document_end":
            new_template = (base_content + "\n\n" + section_content).strip()
        else:
            new_template = (base_content + "\n\n" + section_content).strip()
        
        # 更新临时模板
        memory.report_state.template_content = new_template
        
        logger.info(f"临时模板已更新,长度: {len(new_template)} 字符")
    
    def _estimate_llm_cost(self, text: str) -> float:
        """
        估算LLM调用成本
        
        Args:
            text: 文本内容
        
        Returns:
            float: 估算成本(美元)
        """
        # 简化估算: 每4个字符≈1个token
        tokens = len(text) / 4
        # GPT-4: 输入$0.03/1K tokens, 输出$0.06/1K tokens
        # 假设输入输出各占一半
        cost = (tokens / 1000) * 0.045
        return cost
