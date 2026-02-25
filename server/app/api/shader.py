import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_service import LLMService

router = APIRouter()
logger = logging.getLogger(__name__)


def _try_compile(shader_code: str) -> tuple[str | None, str]:
    """Compile-check *shader_code* inside the fragment wrapper.

    Returns ``(error_or_none, sanitized_code)`` — a 2-tuple so the
    caller always gets back the sanitized version of the code.
    Lazy-imports moderngl so the module still loads if the GPU lib is absent.
    """
    try:
        from app.services.shader_render_service import (
            ShaderRenderService,
        )

        return ShaderRenderService._try_compile(shader_code)
    except Exception as exc:
        logger.debug(
            "Server-side shader compilation unavailable: %s", exc,
        )
        # Can't compile — return the original code unchanged
        return None, shader_code


async def _generate_and_validate(
    llm: LLMService,
    description: str,
    mood_tags: list[str] | None,
    color_palette: list[str] | None,
) -> str:
    """Generate a shader via the LLM with progressive compile-retry.

    Strategy (up to 6 LLM calls before fallback):
      1. Generate a complex shader (full creative freedom)
      2. If it fails, ask the LLM to FIX the exact error (x3)
      3. If fixes fail, generate a fresh shader from scratch
      4. If that fails too, one more fix attempt
      5. Fallback is absolute last resort

    IMPORTANT: _try_compile() returns (error, sanitized_code).
    We always use the *sanitized* version going forward because the
    sanitizer may have injected mainImage, renamed reserved names,
    fixed int literals, etc.  Without this, the retry pipeline would
    pass unsanitized code to fix_shader and lose those fixes.
    """
    # ── Attempt 1: full creative generation ───────────────
    code = await llm.generate_shader(
        description=description,
        mood_tags=mood_tags,
        color_palette=color_palette,
    )
    if not code:
        raise HTTPException(
            status_code=500, detail="Shader generation failed",
        )

    compile_err, code = await asyncio.to_thread(_try_compile, code)
    if compile_err is None:
        logger.info("Shader compiled on first attempt")
        return code

    logger.warning(
        "Initial shader failed compile check: %s", compile_err,
    )

    # ── Attempts 2-4: targeted fix of the broken shader ───
    broken_code = code
    for retry in range(3):
        fixed = await llm.fix_shader(
            previous_code=broken_code,
            compile_error=compile_err,
            description=description,
        )
        if not fixed:
            break

        retry_err, fixed = await asyncio.to_thread(_try_compile, fixed)
        if retry_err is None:
            logger.info(
                "LLM fix compiled on retry %d", retry + 1,
            )
            return fixed

        logger.warning(
            "Fix retry %d still fails: %s", retry + 1, retry_err,
        )
        broken_code = fixed
        compile_err = retry_err

    # ── Attempt 5: fresh generation (still ambitious) ─────
    logger.info(
        "Fix retries exhausted, generating fresh shader",
    )
    fresh = await llm.generate_shader_simple(
        description=description,
        mood_tags=mood_tags,
    )
    if fresh:
        fresh_err, fresh = await asyncio.to_thread(_try_compile, fresh)
        if fresh_err is None:
            logger.info("Fresh shader compiled successfully")
            return fresh
        logger.warning(
            "Fresh shader also failed: %s", fresh_err,
        )

        # ── Attempt 6: one final fix of the fresh shader ─
        final_fix = await llm.fix_shader(
            previous_code=fresh,
            compile_error=fresh_err,
            description=description,
        )
        if final_fix:
            final_err, final_fix = await asyncio.to_thread(
                _try_compile, final_fix,
            )
            if final_err is None:
                logger.info("Final fix compiled successfully")
                return final_fix
            logger.warning(
                "Final fix still fails: %s", final_err,
            )

    # Return whatever we have — downstream fallback catches it
    logger.warning(
        "All shader generation attempts exhausted "
        "(6 LLM calls)",
    )
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
    """Generate a Shadertoy-compatible GLSL fragment shader.

    Uses progressive retry: complex → fix → fix → simple fallback.
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
    code = await llm.fix_shader(
        previous_code=req.previous_code,
        compile_error=req.error,
        description=req.description,
    )
    if not code:
        raise HTTPException(
            status_code=500, detail="Shader retry failed",
        )
    return {"shader_code": code}
