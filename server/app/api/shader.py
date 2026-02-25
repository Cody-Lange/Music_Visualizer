import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_service import LLMService

router = APIRouter()
logger = logging.getLogger(__name__)


class ShaderRequest(BaseModel):
    description: str = Field(..., min_length=1)
    mood_tags: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)


class ShaderRetryRequest(BaseModel):
    description: str = Field(..., min_length=1)
    mood_tags: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    error: str = Field(..., min_length=1)
    previous_code: str = Field(default="")


@router.post("/generate")
async def generate_shader(req: ShaderRequest) -> dict:
    """Generate a Shadertoy-compatible GLSL fragment shader from a description."""
    llm = LLMService()
    code = await llm.generate_shader(
        description=req.description,
        mood_tags=req.mood_tags if req.mood_tags else None,
        color_palette=req.color_palette if req.color_palette else None,
    )
    if not code:
        raise HTTPException(status_code=500, detail="Shader generation failed")
    return {"shader_code": code}


@router.post("/retry")
async def retry_shader(req: ShaderRetryRequest) -> dict:
    """Re-generate a shader after a compilation failure."""
    llm = LLMService()
    code = await llm.generate_shader(
        description=req.description,
        mood_tags=req.mood_tags if req.mood_tags else None,
        color_palette=req.color_palette if req.color_palette else None,
        retry_error=req.error,
        previous_code=req.previous_code if req.previous_code else None,
    )
    if not code:
        raise HTTPException(status_code=500, detail="Shader retry failed")
    return {"shader_code": code}
