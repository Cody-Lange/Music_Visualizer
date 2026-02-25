import json
import logging
import re
from typing import Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.chat import ChatMessage
from app.services.llm_service import LLMService
from app.services.storage import job_store

router = APIRouter()
logger = logging.getLogger(__name__)

ChatPhase = Literal["analysis", "refinement", "confirmation", "rendering", "editing"]

# Patterns that suggest the user wants to render
_CONFIRM_PATTERNS = re.compile(
    r"\b("
    r"yes\s*(,?\s*render|,?\s*go|,?\s*do\s*it|,?\s*please|,?\s*let'?s)|"
    r"render\s*(it|now|the\s*video|this)?|"
    r"make\s*the\s*video|"
    r"start\s*render|"
    r"let'?s\s*(go|do\s*it|render|make)|"
    r"looks?\s*(good|great|perfect)|"
    r"ready\s*to\s*render|"
    r"go\s*ahead|"
    r"do\s*it|"
    r"with\s*ai|"
    r"procedural\s*(only|rendering)?|"
    r"that'?s?\s*(perfect|great|good|awesome)"
    r")\b",
    re.IGNORECASE,
)

# Patterns the LLM uses to ask for render confirmation
_LLM_ASKS_CONFIRM = re.compile(
    r"(ready\s+to\s+render\??|shall\s+(i|we)\s+(start|begin)\s+render|"
    r"proceed\s+with\s+render|confirm\s+to\s+render|want\s+me\s+to\s+render|"
    r"type\s+.?render.?\s+|would\s+you\s+like\s+to\s+enhance)",
    re.IGNORECASE,
)


def _build_analysis_context(job_id: str) -> str:
    """Build a context string from the job's analysis and lyrics data."""
    job = job_store.get_job(job_id)
    if not job:
        return ""

    parts: list[str] = []
    analysis = job.get("analysis")
    if analysis:
        metadata = analysis.get("metadata", {})
        rhythm = analysis.get("rhythm", {})
        tonal = analysis.get("tonal", {})
        mood = analysis.get("mood", {})
        sections = analysis.get("sections", {})

        parts.append("=== AUDIO ANALYSIS ===")
        parts.append(f"File: {metadata.get('filename', 'unknown')}")
        parts.append(f"Duration: {metadata.get('duration', 0):.1f}s")
        parts.append(f"BPM: {rhythm.get('bpm', 0):.1f}")
        parts.append(f"Key: {tonal.get('key', '?')} {tonal.get('scale', '?')}")
        parts.append(f"Mood: valence={mood.get('valence', 0):.2f}, energy={mood.get('energy', 0):.2f}")
        parts.append(f"Mood tags: {', '.join(mood.get('tags', []))}")
        parts.append(f"Danceability: {mood.get('danceability', 0):.2f}")

        boundaries = sections.get("boundaries", [])
        labels = sections.get("labels", [])
        if boundaries and labels:
            parts.append("\nSections:")
            for i, (boundary, label) in enumerate(zip(boundaries, labels)):
                end = boundaries[i + 1] if i + 1 < len(boundaries) else metadata.get("duration", 0)
                parts.append(f"  {label}: {boundary:.1f}s - {end:.1f}s")

    lyrics = job.get("lyrics")
    if lyrics:
        lines = lyrics.get("lines", [])
        if lines:
            parts.append("\n=== LYRICS ===")
            for line in lines:
                text = line.get("text", "")
                if text.strip():
                    parts.append(text)

    return "\n".join(parts)


def _detect_phase_transition(
    phase: ChatPhase,
    user_content: str,
    assistant_response: str,
    turn_count: int,
) -> ChatPhase:
    """Determine if the conversation should move to a new phase."""
    if phase == "analysis":
        # After the initial analysis response, move to refinement
        return "refinement"

    if phase == "refinement":
        # Check if the LLM is asking for render confirmation
        if _LLM_ASKS_CONFIRM.search(assistant_response):
            return "confirmation"
        # Check if the user is directly asking to render
        if _CONFIRM_PATTERNS.search(user_content):
            return "confirmation"
        return "refinement"

    if phase == "confirmation":
        # User confirmed — check if user says yes to render
        if _CONFIRM_PATTERNS.search(user_content):
            return "rendering"
        # User wants more changes — back to refinement
        return "refinement"

    # rendering and editing phases stay as-is until explicitly changed
    return phase


def _try_extract_render_spec(text: str) -> dict | None:
    """Try to extract a JSON render spec from an LLM response."""
    # Look for ```json ... ``` blocks
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try the entire text as JSON
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    return None


@router.websocket("/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for LLM conversation streaming."""
    await websocket.accept()

    llm = LLMService()
    conversation_history: list[ChatMessage] = []
    job_id: str | None = None
    phase: ChatPhase = "analysis"
    turn_count = 0

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "message")

            # Allow client to bind a job_id to this chat session
            if msg_type == "bind_job":
                job_id = data.get("job_id")
                await websocket.send_text(json.dumps({
                    "type": "system",
                    "content": f"Session bound to job {job_id}",
                }))
                continue

            # Regular chat message
            user_content = data.get("content", "")
            if not user_content:
                continue

            conversation_history.append(ChatMessage(role="user", content=user_content))
            turn_count += 1

            # Build context from analysis data
            context = _build_analysis_context(job_id) if job_id else ""

            # Early detection: if user is confirming render, skip streaming
            # the JSON and go straight to render spec extraction
            will_render = (
                phase == "confirmation"
                and _CONFIRM_PATTERNS.search(user_content)
            )

            if will_render:
                # Transition to rendering phase immediately
                phase = "rendering"
                await websocket.send_text(json.dumps({
                    "type": "phase",
                    "phase": phase,
                }))
                await websocket.send_text(json.dumps({
                    "type": "system",
                    "content": "Generating render specification...",
                }))

                # Extract render spec from conversation (don't stream
                # the JSON response to the chat)
                render_spec = await llm.extract_render_spec(
                    conversation_history, context
                )

                if render_spec:
                    # Determine AI keyframes preference
                    use_ai = render_spec.pop("useAiKeyframes", False)
                    use_ai_video = False
                    if re.search(r"\bwith\s+ai\s+video\b", user_content, re.IGNORECASE):
                        use_ai = True
                        use_ai_video = True
                    elif re.search(r"\bwith\s+ai\b", user_content, re.IGNORECASE):
                        use_ai = True

                    # Store on the job
                    if job_id:
                        job_store.update_job(job_id, {
                            "render_spec": render_spec,
                            "use_ai_keyframes": use_ai,
                            "use_ai_video": use_ai_video,
                        })

                    mode_label = (
                        "AI video generation enabled."
                        if use_ai_video
                        else "AI keyframes enabled."
                        if use_ai
                        else "Procedural rendering."
                    )
                    await websocket.send_text(json.dumps({
                        "type": "system",
                        "content": (
                            f"Render spec ready! {mode_label} Starting render..."
                        ),
                    }))

                    await websocket.send_text(json.dumps({
                        "type": "render_spec",
                        "render_spec": render_spec,
                    }))
                else:
                    # Extraction failed — go back to confirmation
                    phase = "confirmation"
                    await websocket.send_text(json.dumps({
                        "type": "phase",
                        "phase": phase,
                    }))
                    await websocket.send_text(json.dumps({
                        "type": "system",
                        "content": "I had trouble generating the render spec. Could you confirm once more?",
                    }))

                continue  # Skip normal streaming for this turn

            # ── Normal streaming path ──────────────────────────────

            # Send current phase info
            await websocket.send_text(json.dumps({
                "type": "phase",
                "phase": phase,
            }))

            # Stream LLM response
            await websocket.send_text(json.dumps({
                "type": "stream_start",
            }))

            full_response = ""
            async for chunk in llm.stream_chat(conversation_history, context):
                full_response += chunk
                await websocket.send_text(json.dumps({
                    "type": "stream_chunk",
                    "content": chunk,
                }))

            conversation_history.append(ChatMessage(role="assistant", content=full_response))

            await websocket.send_text(json.dumps({
                "type": "stream_end",
                "content": full_response,
            }))

            # Detect phase transitions
            new_phase = _detect_phase_transition(phase, user_content, full_response, turn_count)
            if new_phase != phase:
                phase = new_phase
                await websocket.send_text(json.dumps({
                    "type": "phase",
                    "phase": phase,
                }))

    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected: session=%s", session_id)
    except Exception:
        logger.exception("Chat WebSocket error: session=%s", session_id)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
