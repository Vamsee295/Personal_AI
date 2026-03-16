"""
api/screen_routes.py – Dedicated screen AI endpoint that combines capture + OCR + AI analysis.
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.services.ai_service import ai_service
from app.utils.logger import get_logger

logger = get_logger("screen_routes")

router = APIRouter(prefix="/api/screen", tags=["Screen AI"])

_SCREEN_SYSTEM = (
    "You are Vamsee AI, an intelligent screen reader assistant. "
    "The user will give you raw text extracted from their screen via OCR. "
    "Your job is to analyse what you see — identify errors, summarise the content, "
    "and give clear actionable advice. Be concise and direct."
)


@router.get("/analyse")
async def analyse_screen():
    """
    1. Capture the screen
    2. Run OCR to extract text
    3. Send to AI for analysis
    4. Return screen text + AI explanation
    """
    try:
        from app.agents.screen_agent import screen_agent

        # Step 1: Capture
        image_bytes = screen_agent.capture_screen()

        # Step 2: OCR
        screen_text = screen_agent.extract_text(image_bytes)

        if not screen_text.strip():
            screen_text = "(No readable text found on screen)"

        # Step 3: AI analysis
        from app.models.schemas import ChatMessage
        prompt = (
            f"The following text was extracted from my screen via OCR:\n\n"
            f"---\n{screen_text[:3000]}\n---\n\n"
            f"Please analyse this. If you see errors, explain them and suggest fixes. "
            f"If you see code, describe what it does. Otherwise summarise what is on the screen."
        )

        analysis = await ai_service.chat(
            message=prompt,
            history=[ChatMessage(role="system", content=_SCREEN_SYSTEM)],
            model="qwen2.5-coder:7b",
        )

        import base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        return {
            "screen_text": screen_text,
            "analysis": analysis,
            "image_base64": image_b64,
        }

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Screen analyse error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/text")
async def get_screen_text():
    """Pure OCR – just return raw text from screen without AI analysis."""
    try:
        from app.agents.screen_agent import screen_agent
        text = screen_agent.extract_text()
        return {"text": text, "success": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
