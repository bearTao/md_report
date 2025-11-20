"""System configuration API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models.db_models import AIProviderKey, AgentLLMConfig
from app.schemas.api_schemas import (
    AIConfigResponse, 
    AIConfigUpdate,
    AgentConfigResponse,
    AgentConfigUpdate,
    AgentLLMConfigItem
)


router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/ai", response_model=AIConfigResponse)
async def get_ai_config(db: Session = Depends(get_db)):
    """Get AI configuration status"""
    # Check environment variable first
    env_key = os.getenv("OPENAI_API_KEY")
    env_base = os.getenv("OPENAI_API_BASE")
    if env_key:
        return AIConfigResponse(
            configured=True,
            provider="openai",
            api_base=env_base
        )
    
    # Check database
    config = db.query(AIProviderKey).filter(
        AIProviderKey.provider == "openai"
    ).first()
    
    if config:
        return AIConfigResponse(
            configured=True,
            provider="openai",
            api_base=config.api_base
        )
    
    return AIConfigResponse(
        configured=False,
        provider=None,
        api_base=None
    )


@router.put("/ai", response_model=AIConfigResponse)
async def update_ai_config(
    config_data: AIConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update AI configuration"""
    # For P0, store plaintext (in production, use proper encryption)
    # Check if config exists
    existing = db.query(AIProviderKey).filter(
        AIProviderKey.provider == config_data.provider
    ).first()
    
    if existing:
        existing.api_key_ciphertext = config_data.api_key
        existing.api_base = config_data.api_base
        db.commit()
    else:
        new_config = AIProviderKey(
            provider=config_data.provider,
            api_key_ciphertext=config_data.api_key,
            api_base=config_data.api_base
        )
        db.add(new_config)
        db.commit()
    
    return AIConfigResponse(
        configured=True,
        provider=config_data.provider,
        api_base=config_data.api_base
    )


@router.get("/agent", response_model=AgentConfigResponse)
async def get_agent_config(db: Session = Depends(get_db)):
    """获取Agent配置"""
    # 查询所有组件的配置
    configs = db.query(AgentLLMConfig).all()
    
    # 转换为字典格式
    config_dict = {}
    for config in configs:
        config_dict[config.component] = AgentLLMConfigItem(
            component=config.component,
            model=config.model,
            api_key=config.api_key,
            api_base=config.api_base,
            organization=config.organization,
            temperature=float(config.temperature),
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            enabled=config.enabled
        )
    
    # 如果某些组件没有配置，使用默认值
    default_configs = {
        "intent_parser": AgentLLMConfigItem(
            component="intent_parser",
            model="gpt-4",
            temperature=0.1,
            timeout=60,
            enabled=True
        ),
        "explanation_generator": AgentLLMConfigItem(
            component="explanation_generator",
            model="gpt-3.5-turbo",
            temperature=0.7,
            timeout=30,
            enabled=False
        ),
        "ai_refinement": AgentLLMConfigItem(
            component="ai_refinement",
            model="gpt-4",
            temperature=0.7,
            timeout=90,
            enabled=True
        ),
    }
    
    # 合并默认配置和数据库配置
    for component, default_config in default_configs.items():
        if component not in config_dict:
            config_dict[component] = default_config
    
    return AgentConfigResponse(configs=config_dict)


@router.put("/agent", response_model=AgentConfigResponse)
async def update_agent_config(
    config_data: AgentConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新Agent配置"""
    # 检查组件名称是否有效
    valid_components = ["intent_parser", "explanation_generator", "ai_refinement"]
    if config_data.component not in valid_components:
        raise HTTPException(
            status_code=400,
            detail=f"无效的组件名称。有效值: {', '.join(valid_components)}"
        )
    
    # 查找现有配置
    existing = db.query(AgentLLMConfig).filter(
        AgentLLMConfig.component == config_data.component
    ).first()
    
    if existing:
        # 更新现有配置
        existing.model = config_data.model
        existing.api_key = config_data.api_key
        existing.api_base = config_data.api_base
        existing.organization = config_data.organization
        existing.temperature = config_data.temperature
        existing.max_tokens = config_data.max_tokens
        existing.timeout = config_data.timeout
        existing.enabled = config_data.enabled
    else:
        # 创建新配置
        new_config = AgentLLMConfig(
            component=config_data.component,
            model=config_data.model,
            api_key=config_data.api_key,
            api_base=config_data.api_base,
            organization=config_data.organization,
            temperature=config_data.temperature,
            max_tokens=config_data.max_tokens,
            timeout=config_data.timeout,
            enabled=config_data.enabled
        )
        db.add(new_config)
    
    db.commit()
    
    # 重新加载配置并返回
    return await get_agent_config(db)

