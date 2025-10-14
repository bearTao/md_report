"""System configuration API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models.db_models import AIProviderKey
from app.schemas.api_schemas import AIConfigResponse, AIConfigUpdate


router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/ai", response_model=AIConfigResponse)
async def get_ai_config(db: Session = Depends(get_db)):
    """Get AI configuration status"""
    # Check environment variable first
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return AIConfigResponse(
            configured=True,
            provider="openai"
        )
    
    # Check database
    config = db.query(AIProviderKey).filter(
        AIProviderKey.provider == "openai"
    ).first()
    
    if config:
        return AIConfigResponse(
            configured=True,
            provider="openai"
        )
    
    return AIConfigResponse(
        configured=False,
        provider=None
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
        db.commit()
    else:
        new_config = AIProviderKey(
            provider=config_data.provider,
            api_key_ciphertext=config_data.api_key
        )
        db.add(new_config)
        db.commit()
    
    return AIConfigResponse(
        configured=True,
        provider=config_data.provider
    )

