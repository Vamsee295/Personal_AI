"""
api/chat_routes.py – REST + WebSocket endpoints for AI chat and code generation.
"""

from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatRequest, ChatResponse,
    CodeGenerationRequest, CodeGenerationResponse,
    SuccessResponse,
)
from app.services.ai_service import ai_service
from app.utils.logger import get_logger

logger = get_logger("chat_routes")

router = APIRouter(prefix="/api", tags=["AI Chat"])


# ══════════════════════════════════════════════════════════════════
#  Health / models
# ══════════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Quick health check – also verifies Ollama is accessible."""
    running = ai_service.ollama_running()
    return {
        "status": "ok",
        "ollama_running": running,
    }


@router.get("/models")
async def list_models():
    """List all locally available Ollama models."""
    models = await ai_service.available_models()
    return {"models": models}


# ══════════════════════════════════════════════════════════════════
#  Chat
# ══════════════════════════════════════════════════════════════════

@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Send a chat message and receive an AI response.
    If req.stream=True the response body is a text/event-stream.
    """
    if req.stream:
        async def _generator():
            async for token in ai_service.chat_stream(req.message, req.history, req.model):
                yield f"data: {token}\n\n"

        return StreamingResponse(_generator(), media_type="text/event-stream")

    response = await ai_service.chat(req.message, req.history, req.model)
    return ChatResponse(response=response, model=req.model or "default")


# ══════════════════════════════════════════════════════════════════
#  Chat via WebSocket (streaming tokens)
# ══════════════════════════════════════════════════════════════════

@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time AI chat.
    Client sends: {"message": "...", "model": "..."}  (JSON)
    Server sends:  each token, then {"done": true}
    """
    await websocket.accept()
    logger.info("WebSocket /ws/chat connected")

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            model = data.get("model")
            history_raw = data.get("history", [])

            from app.models.schemas import ChatMessage
            history = [ChatMessage(**h) for h in history_raw]

            async for token in ai_service.chat_stream(message, history, model):
                await websocket.send_text(token)

            await websocket.send_json({"done": True})

    except WebSocketDisconnect:
        logger.info("WebSocket /ws/chat disconnected")


# ══════════════════════════════════════════════════════════════════
#  Code generation
# ══════════════════════════════════════════════════════════════════

@router.post("/generate-code")
async def generate_code(req: CodeGenerationRequest):
    """Generate code from a natural-language prompt."""
    if req.stream:
        async def _generator():
            async for token in ai_service.generate_code_stream(
                req.prompt, req.language or "python", req.context, req.model
            ):
                yield f"data: {token}\n\n"

        return StreamingResponse(_generator(), media_type="text/event-stream")

    code = await ai_service.generate_code(
        req.prompt, req.language or "python", req.context, req.model
    )
    return CodeGenerationResponse(code=code, language=req.language or "python")


@router.websocket("/ws/generate-code")
async def ws_generate_code(websocket: WebSocket):
    """WebSocket for streaming code generation."""
    await websocket.accept()
    logger.info("WebSocket /ws/generate-code connected")

    try:
        while True:
            data = await websocket.receive_json()
            prompt = data.get("prompt", "")
            language = data.get("language", "python")
            context = data.get("context")
            model = data.get("model")

            async for token in ai_service.generate_code_stream(prompt, language, context, model):
                await websocket.send_text(token)

            await websocket.send_json({"done": True})

    except WebSocketDisconnect:
        logger.info("WebSocket /ws/generate-code disconnected")
