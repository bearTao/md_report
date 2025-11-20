"""
Agent配置管理模块

本模块负责加载和管理Agent相关的配置,包括:
- LLM模型配置
- API密钥和基础URL
- 各个Agent组件的特定配置

配置来源优先级:
1. 环境变量
2. 本地配置文件
3. 默认值
"""
import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """LLM模型配置"""
    model: str = Field(default="gpt-3.5-turbo", description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    api_base: Optional[str] = Field(default=None, description="API基础URL")
    organization: Optional[str] = Field(default=None, description="组织ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: Optional[int] = Field(default=None, description="最大生成token数")
    timeout: int = Field(default=60, description="请求超时时间(秒)")


class APIConfig(BaseModel):
    """API配置"""
    api_key: Optional[str] = Field(default=None, description="API密钥")
    api_base: Optional[str] = Field(default=None, description="API基础URL")
    organization: Optional[str] = Field(default=None, description="组织ID")


class IntentParserConfig(BaseModel):
    """意图解析器配置"""
    llm: LLMConfig = Field(default_factory=lambda: LLMConfig(
        model="gpt-4",
        temperature=0.1
    ))
    enabled: bool = Field(default=True, description="是否启用")
    max_retries: int = Field(default=2, description="最大重试次数")
    use_db_config: bool = Field(default=True, description="是否使用数据库配置")


class ExplanationGeneratorConfig(BaseModel):
    """响应生成器配置"""
    use_llm: bool = Field(default=False, description="是否使用LLM生成")
    llm: LLMConfig = Field(default_factory=lambda: LLMConfig(
        model="gpt-3.5-turbo",
        temperature=0.7
    ))
    use_db_config: bool = Field(default=True, description="是否使用数据库配置")


class AIRefinementConfig(BaseModel):
    """AI内容优化配置"""
    llm: LLMConfig = Field(default_factory=lambda: LLMConfig(
        model="gpt-4",
        temperature=0.7
    ))
    fallback_enabled: bool = Field(default=True, description="是否启用fallback模式")
    use_db_config: bool = Field(default=True, description="是否使用数据库配置")


class AgentConfig(BaseModel):
    """Agent完整配置"""
    api: APIConfig = Field(default_factory=APIConfig)
    intent_parser: IntentParserConfig = Field(default_factory=IntentParserConfig)
    explanation_generator: ExplanationGeneratorConfig = Field(default_factory=ExplanationGeneratorConfig)
    ai_refinement: AIRefinementConfig = Field(default_factory=AIRefinementConfig)
    
    # 通用配置
    log_level: str = Field(default="INFO", description="日志级别")
    enable_performance_tracking: bool = Field(default=True, description="是否启用性能追踪")


class ConfigManager:
    """
    配置管理器
    
    负责加载、合并和提供配置。
    配置来源优先级: 环境变量 > 配置文件 > 默认值
    """
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[AgentConfig] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> AgentConfig:
        """
        加载配置
        
        Returns:
            AgentConfig: 完整的配置对象
        """
        # 1. 从配置文件加载
        file_config = self._load_from_file()
        
        # 2. 从环境变量覆盖
        env_config = self._load_from_env()
        
        # 3. 合并配置
        merged_config = self._merge_configs(file_config, env_config)
        
        logger.info("Agent配置加载完成")
        return merged_config
    
    def _load_from_db(self, component: str):
        """
        从数据库加载特定组件的LLM配置
        
        Args:
            component: 组件名称 (intent_parser, explanation_generator, ai_refinement)
        
        Returns:
            Dict[str, Any]: 数据库配置字典，如果没有配置则返回空字典
        """
        try:
            from app.database import SessionLocal
            from app.models.db_models import AgentLLMConfig
            
            db = SessionLocal()
            try:
                db_config = db.query(AgentLLMConfig).filter(
                    AgentLLMConfig.component == component
                ).first()
                
                if db_config and db_config.enabled:
                    return {
                        "model": db_config.model,
                        "api_key": db_config.api_key,
                        "api_base": db_config.api_base,
                        "organization": db_config.organization,
                        "temperature": float(db_config.temperature),
                        "max_tokens": db_config.max_tokens,
                        "timeout": db_config.timeout,
                    }
                return {}
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"从数据库加载{component}配置失败: {e}")
            return {}
    
    def _load_from_file(self) -> Dict[str, Any]:
        """
        从配置文件加载
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        # 查找配置文件
        config_paths = [
            Path("config/agent_config.yaml"),
            Path("config/agent_config.yml"),
            Path("agent_config.yaml"),
            Path("agent_config.yml"),
        ]
        
        # 支持通过环境变量指定配置文件路径
        custom_path = os.getenv("AGENT_CONFIG_PATH")
        if custom_path:
            config_paths.insert(0, Path(custom_path))
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    logger.info(f"从配置文件加载配置: {config_path}")
                    return config_data or {}
                except Exception as e:
                    logger.warning(f"加载配置文件失败: {config_path}, 错误: {e}")
        
        logger.info("未找到配置文件,使用默认配置")
        return {}
    
    def _load_from_env(self) -> Dict[str, Any]:
        """
        从环境变量加载
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        env_config: Dict[str, Any] = {}
        
        # API配置
        if os.getenv("OPENAI_API_KEY"):
            env_config.setdefault("api", {})
            env_config["api"]["api_key"] = os.getenv("OPENAI_API_KEY")
        
        if os.getenv("OPENAI_API_BASE"):
            env_config.setdefault("api", {})
            env_config["api"]["api_base"] = os.getenv("OPENAI_API_BASE")
        
        if os.getenv("OPENAI_ORGANIZATION"):
            env_config.setdefault("api", {})
            env_config["api"]["organization"] = os.getenv("OPENAI_ORGANIZATION")
        
        # 日志级别
        if os.getenv("AGENT_LOG_LEVEL"):
            env_config["log_level"] = os.getenv("AGENT_LOG_LEVEL")
        
        # Intent Parser配置
        if os.getenv("INTENT_PARSER_MODEL"):
            env_config.setdefault("intent_parser", {}).setdefault("llm", {})
            env_config["intent_parser"]["llm"]["model"] = os.getenv("INTENT_PARSER_MODEL")
        
        if os.getenv("INTENT_PARSER_TEMPERATURE"):
            env_config.setdefault("intent_parser", {}).setdefault("llm", {})
            env_config["intent_parser"]["llm"]["temperature"] = float(os.getenv("INTENT_PARSER_TEMPERATURE"))
        
        # AI Refinement配置
        if os.getenv("AI_REFINEMENT_MODEL"):
            env_config.setdefault("ai_refinement", {}).setdefault("llm", {})
            env_config["ai_refinement"]["llm"]["model"] = os.getenv("AI_REFINEMENT_MODEL")
        
        if os.getenv("AI_REFINEMENT_TEMPERATURE"):
            env_config.setdefault("ai_refinement", {}).setdefault("llm", {})
            env_config["ai_refinement"]["llm"]["temperature"] = float(os.getenv("AI_REFINEMENT_TEMPERATURE"))
        
        if env_config:
            logger.info("从环境变量加载配置")
        
        return env_config
    
    def _merge_configs(self, file_config: Dict[str, Any], env_config: Dict[str, Any]) -> AgentConfig:
        """
        合并配置
        
        Args:
            file_config: 文件配置
            env_config: 环境变量配置
        
        Returns:
            AgentConfig: 合并后的配置对象
        """
        # 深度合并字典
        merged = self._deep_merge(file_config, env_config)
        
        # 验证并创建配置对象
        try:
            config = AgentConfig(**merged)
            return config
        except Exception as e:
            logger.error(f"配置验证失败: {e}, 使用默认配置")
            return AgentConfig()
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典
        
        Args:
            base: 基础字典
            override: 覆盖字典
        
        Returns:
            Dict[str, Any]: 合并后的字典
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_config(self) -> AgentConfig:
        """
        获取配置
        
        Returns:
            AgentConfig: 配置对象
        """
        return self._config
    
    def reload_config(self) -> AgentConfig:
        """
        重新加载配置
        
        Returns:
            AgentConfig: 新的配置对象
        """
        self._config = self._load_config()
        return self._config
    
    def get_llm_kwargs(self, component: str) -> Dict[str, Any]:
        """
        获取LLM初始化参数
        
        Args:
            component: 组件名称 (intent_parser, explanation_generator, ai_refinement)
        
        Returns:
            Dict[str, Any]: LLM初始化参数
        """
        config = self.get_config()
        
        # 获取组件配置
        if component == "intent_parser":
            component_config = config.intent_parser
            llm_config = component_config.llm
        elif component == "explanation_generator":
            component_config = config.explanation_generator
            llm_config = component_config.llm
        elif component == "ai_refinement":
            component_config = config.ai_refinement
            llm_config = component_config.llm
        else:
            raise ValueError(f"未知的组件: {component}")
        
        # 尝试从数据库加载配置
        db_config = {}
        if hasattr(component_config, 'use_db_config') and component_config.use_db_config:
            db_config = self._load_from_db(component)
        
        # 构建参数，优先使用数据库配置
        kwargs = {
            "model": db_config.get("model") or llm_config.model,
            "temperature": db_config.get("temperature") if db_config.get("temperature") is not None else llm_config.temperature,
            "timeout": db_config.get("timeout") or llm_config.timeout,
        }
        
        # max_tokens
        max_tokens = db_config.get("max_tokens") or llm_config.max_tokens
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        # API配置：优先使用数据库配置，其次是LLM配置，最后是全局API配置
        api_key = db_config.get("api_key") or llm_config.api_key or config.api.api_key
        if api_key:
            kwargs["api_key"] = api_key
        
        api_base = db_config.get("api_base") or llm_config.api_base or config.api.api_base
        if api_base:
            kwargs["base_url"] = api_base
        
        organization = db_config.get("organization") or llm_config.organization or config.api.organization
        if organization:
            kwargs["organization"] = organization
        
        return kwargs


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> AgentConfig:
    """
    获取全局配置
    
    Returns:
        AgentConfig: 配置对象
    """
    return config_manager.get_config()


def get_llm_kwargs(component: str) -> Dict[str, Any]:
    """
    获取LLM初始化参数
    
    Args:
        component: 组件名称
    
    Returns:
        Dict[str, Any]: LLM初始化参数
    """
    return config_manager.get_llm_kwargs(component)
