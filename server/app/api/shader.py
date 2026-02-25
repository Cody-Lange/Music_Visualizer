import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_service import LLMService

router = APIRouter()
logger = logging.getLogger(__name__)

# Maximum number of LLM fix-up rounds when the generated shader fails to compile.
_MAX_COMPILE_RETRIES = 3


def _try_compile(shader_code: str) -> str | None:
    """Compile-check *shader_code* inside the fragment wrapper.

    Returns ``None`` on success, or the error message string on failure.
    Lazy-imports moderngl so the module still loads if the GPU lib is absent.
    """
    try:
        from app.services.shader_render_service import (
            ShaderRenderService,
        )

        return ShaderRenderService._try_compile(shader_code)
    except Exception as exc:
        # If moderngl is unavailable, skip server-side validation.
        logger.debug("Server-side shader compilation unavailable: %s", exc)
        return None


async def _generate_and_validate(
    llm: LLMService,
    description: str,
    mood_tags: list[str] | None,
    color_palette: list[str] | None,
) -> str:
    """Generate a shader via the LLM and validate it server-side.

    If the first attempt doesn't compile, the LLM is asked to fix it
    up to ``_MAX_COMPILE_RETRIES`` times.  Returns the first shader that
    compiles successfully, or the last attempt if all retries are exhausted
    (the client / render pipeline has its own fallback).
    """
    code = await llm.generate_shader(
        description=description,
        mood_tags=mood_tags,
        color_palette=color_palette,
    )
    if not code:
        raise HTTPException(status_code=500, detail="Shader generation failed")

    # Compile-check
    compile_err = await asyncio.to_thread(_try_compile, code)
    if compile_err is None:
        return code

    logger.warning("Initial shader failed compile check: %s", compile_err)

    broken_code = code
    for retry in range(_MAX_COMPILE_RETRIES):
        fixed = await llm.generate_shader(
            description=description,
            mood_tags=mood_tags,
            color_palette=color_palette,
            retry_error=compile_err,
            previous_code=broken_code,
        )
        if not fixed:
            break

        retry_err = await asyncio.to_thread(_try_compile, fixed)
        if retry_err is None:
            logger.info("LLM-fixed shader compiled on generate retry %d", retry + 1)
            return fixed

        logger.warning(
            "Generate retry %d still fails: %s", retry + 1, retry_err
        )
        broken_code = fixed
        compile_err = retry_err

    # Return the last attempt — downstream has its own fallback
    logger.warning("All generate retries exhausted, returning last attempt")
    return broken_code


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
    """Generate a Shadertoy-compatible GLSL fragment shader from a description.

    The shader is compile-checked server-side; on failure the LLM is asked to
    fix it (up to 3 retries) before returning.
    """
    llm = LLMService()
    code = await _generate_and_validate(
        llm,
        description=req.description,
        mood_tags=req.mood_tags if req.mood_tags else None,
        color_palette=req.color_palette if req.color_palette else None,
    )
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
