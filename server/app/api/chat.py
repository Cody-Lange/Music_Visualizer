import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.chat import ChatMessage
from app.services.llm_service import LLMService
from app.services.storage import job_store

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.websocket("/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for LLM conversation streaming."""
    await websocket.accept()

    llm = LLMService()
    conversation_history: list[ChatMessage] = []
    job_id: str | None = None

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

            # Build context from analysis data
            context = _build_analysis_context(job_id) if job_id else ""

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

    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected: session=%s", session_id)
    except Exception:
        logger.exception("Chat WebSocket error: session=%s", session_id)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
