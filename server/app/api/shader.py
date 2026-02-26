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


async def _compile_or_none(code: str) -> tuple[str | None, str]:
    """Compile-check in a thread.  Returns (error, sanitized_code)."""
    return await asyncio.to_thread(_try_compile, code)


_MISSING_ENTRY = "missing required entry point"


async def _try_fix_entry_point(
    llm: LLMService,
    code: str,
    compile_err: str,
    description: str,
) -> tuple[str | None, str]:
    """If compile_err is a missing-mainImage error, ask the LLM to fix it.

    Returns the (possibly updated) (compile_err, code) pair.  If the
    error isn't about a missing entry point, returns unchanged.
    """
    if _MISSING_ENTRY not in compile_err.lower():
        return compile_err, code
    logger.info("Missing mainImage — asking LLM ensure_entry_point")
    fixed = await llm.ensure_entry_point(code, description)
    new_err, fixed = await _compile_or_none(fixed)
    if new_err is None:
        logger.info("ensure_entry_point fixed the shader")
        return None, fixed
    logger.warning("After ensure_entry_point: %s", new_err)
    return new_err, fixed


async def _generate_and_validate(
    llm: LLMService,
    description: str,
    mood_tags: list[str] | None,
    color_palette: list[str] | None,
) -> str:
    """Generate a shader via the LLM and validate with compile checks.

    Pipeline — uses the LLM for *all* semantic fixes (not regex):
      1. Generate a complex shader → compile-check
      2. If missing mainImage → LLM ensure_entry_point()
      3. If error → LLM validate_shader() (full-code review)
      4. Re-check mainImage after validate_shader (it often forgets)
      5. Still failing → LLM fix_shader() retries
      6. Still failing → fresh generation from scratch
      7. Curated fallback as absolute last resort

    _try_compile() returns (error, sanitized_code) — the mechanical
    sanitizer (strip markdown, rename hash→hashFn, fix int literals,
    etc.) runs inside every _try_compile() call automatically.
    """
    # ── Step 1: full creative generation ───────────────────
    code = await llm.generate_shader(
        description=description,
        mood_tags=mood_tags,
        color_palette=color_palette,
    )
    if not code:
        raise HTTPException(
            status_code=500, detail="Shader generation failed",
        )

    compile_err, code = await _compile_or_none(code)
    if compile_err is None:
        logger.info("Shader compiled on first attempt")
        return code

    logger.warning("Initial compile failed: %s", compile_err)

    # ── Step 2: LLM-based structural fix ───────────────────
    compile_err, code = await _try_fix_entry_point(
        llm, code, compile_err, description,
    )
    if compile_err is None:
        return code

    # ── Step 3: LLM full-code review ──────────────────────
    # The LLM reads the entire shader + error, identifies ALL issues
    # (not just the first compiler error), and fixes them in one pass.
    if compile_err:
        logger.info("Asking LLM to review and fix all issues")
        reviewed = await llm.validate_shader(
            code=code,
            compile_error=compile_err,
            description=description,
        )
        if reviewed:
            from app.services.llm_service import sanitize_shader_code

            reviewed = sanitize_shader_code(reviewed)
            review_err, reviewed = await _compile_or_none(reviewed)
            if review_err is None:
                logger.info("LLM validate_shader fixed the shader")
                return reviewed
            logger.warning("After validate_shader: %s", review_err)
            code = reviewed
            compile_err = review_err

            # Re-check: validate_shader often fixes syntax but forgets
            # to add mainImage.  Give ensure_entry_point another shot.
            compile_err, code = await _try_fix_entry_point(
                llm, code, compile_err, description,
            )
            if compile_err is None:
                return code

    # ── Step 4: targeted fix retries ──────────────────────
    if compile_err:
        broken_code = code
        for retry in range(2):
            fixed = await llm.fix_shader(
                previous_code=broken_code,
                compile_error=compile_err,
                description=description,
            )
            if not fixed:
                break
            retry_err, fixed = await _compile_or_none(fixed)
            if retry_err is None:
                logger.info("fix_shader succeeded on retry %d", retry + 1)
                return fixed
            logger.warning(
                "fix_shader retry %d: %s", retry + 1, retry_err,
            )
            # Check if we've regressed to missing mainImage
            retry_err, fixed = await _try_fix_entry_point(
                llm, fixed, retry_err, description,
            )
            if retry_err is None:
                return fixed
            broken_code = fixed
            compile_err = retry_err

    # ── Step 5: fresh generation from scratch ─────────────
    logger.info("All fixes exhausted — generating fresh shader")
    fresh = await llm.generate_shader_simple(
        description=description,
        mood_tags=mood_tags,
    )
    if fresh:
        fresh_err, fresh = await _compile_or_none(fresh)
        if fresh_err is None:
            logger.info("Fresh shader compiled successfully")
            return fresh
        logger.warning("Fresh shader failed: %s", fresh_err)

        # Try ensure_entry_point on fresh code too
        fresh_err, fresh = await _try_fix_entry_point(
            llm, fresh, fresh_err, description,
        )
        if fresh_err is None:
            return fresh

        if fresh_err:
            # One final LLM review of the fresh attempt
            final = await llm.validate_shader(
                code=fresh,
                compile_error=fresh_err,
                description=description,
            )
            if final:
                from app.services.llm_service import sanitize_shader_code

                final = sanitize_shader_code(final)
                final_err, final = await _compile_or_none(final)
                if final_err is None:
                    logger.info("Final validate_shader fixed fresh shader")
                    return final
                logger.warning(
                    "Final validation still fails: %s", final_err,
                )

    # ── Step 6: curated fallback ──────────────────────────
    logger.warning(
        "All LLM attempts exhausted — using curated fallback for '%s'",
        description[:80],
    )
    from app.services.shader_render_service import pick_fallback_shader

    return pick_fallback_shader(description)


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
