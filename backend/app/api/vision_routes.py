"""
api/vision_routes.py -- Vision AI endpoints.

POST /api/vision/analyze-screen
    Captures screen, runs OCR, sends to Ollama.
    Returns the action JSON but does NOT execute it (user confirmation step).

POST /api/vision/vision-loop
    Body: {"goal": "...", "max_steps": 5}
    Runs the full autonomous vision -> decide -> act loop.
    Returns a detailed log of every step.

GET /api/vision/screenshot
    Captures and returns the current screen as a base64-encoded PNG.

GET /api/vision/ocr
    Captures screen and returns raw OCR text only.
"""

from __future__ import annotations

import asyncio
import base64
import io
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("vision_routes")

router = APIRouter(prefix="/api/vision", tags=["Vision AI"])


# ── Pydantic models ────────────────────────────────────────────────────────────

class AnalyzeScreenRequest(BaseModel):
    goal: str = Field(..., description="What the user wants the agent to achieve")
    model: Optional[str] = Field(None, description="Override Ollama model")


class VisionLoopRequest(BaseModel):
    goal: str = Field(..., description="The high-level goal for the autonomous loop")
    max_steps: int = Field(5, ge=1, le=20, description="Max loop iterations (1-20)")
    model: Optional[str] = Field(None, description="Override Ollama model")
    step_delay: float = Field(1.0, ge=0.0, le=10.0, description="Seconds between steps")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_model(requested: Optional[str]) -> str:
    return requested or settings.DEFAULT_MODEL


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/screenshot")
async def get_screenshot():
    """
    Capture the current screen and return it as a base64-encoded PNG.
    Useful for the frontend to display a live preview.
    """
    try:
        from app.agents.vision_module import capture_full_screen

        img = await asyncio.to_thread(capture_full_screen, False)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return {
            "success": True,
            "image_base64": b64,
            "width": img.width,
            "height": img.height,
        }
    except Exception as exc:
        logger.error("Screenshot endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/ocr")
async def get_screen_ocr():
    """
    Capture the screen and return the raw OCR-extracted text.
    Quick check to verify Tesseract is working correctly.
    """
    try:
        from app.agents.vision_module import extract_text_from_screen

        text = await asyncio.to_thread(extract_text_from_screen)
        return {
            "success": True,
            "text": text,
            "char_count": len(text),
            "is_empty": len(text.strip()) == 0,
        }
    except Exception as exc:
        logger.error("OCR endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/analyze-screen")
async def analyze_screen(req: AnalyzeScreenRequest):
    """
    Full vision analysis pipeline -- DOES NOT execute the action.

    1. Capture the current screen.
    2. Run OCR.
    3. Send goal + screen text to Ollama.
    4. Return the suggested action JSON for user confirmation.
    """
    model = _get_model(req.model)
    logger.info("POST /analyze-screen | goal=%r | model=%s", req.goal[:80], model)

    try:
        from app.agents.vision_module import (
            capture_full_screen,
            extract_text_from_image,
            analyze_screen_with_llm,
        )

        # Steps 1 + 2 in threadpool (blocking I/O)
        img = await asyncio.to_thread(capture_full_screen, True)
        screen_text = await asyncio.to_thread(extract_text_from_image, img)

        # Step 3: LLM (also blocking -- uses requests internally)
        action = await asyncio.to_thread(
            analyze_screen_with_llm,
            req.goal,
            screen_text,
            settings.OLLAMA_BASE_URL,
            model,
        )

        return {
            "success": True,
            "goal": req.goal,
            "screen_text_preview": screen_text[:500] if screen_text else "(empty)",
            "screen_text_char_count": len(screen_text),
            "suggested_action": action,
            "note": "Action has NOT been executed. POST to /api/execute/direct to run it.",
        }

    except RuntimeError as exc:
        # Known operational errors (Ollama down, Tesseract missing, etc.)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("analyze-screen error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/vision-loop")
async def run_vision_loop(req: VisionLoopRequest):
    """
    Fully autonomous vision -> OCR -> LLM -> execute loop.

    The agent will:
      1. See the screen
      2. Decide the next action based on your goal
      3. Execute it
      4. Repeat up to max_steps times (or until LLM returns 'done')

    Returns a complete step-by-step log.
    """
    model = _get_model(req.model)
    logger.info(
        "POST /vision-loop | goal=%r | max_steps=%d | model=%s",
        req.goal[:80], req.max_steps, model,
    )

    try:
        from app.agents.vision_module import run_vision_action_loop

        step_log = await asyncio.to_thread(
            run_vision_action_loop,
            req.goal,
            req.max_steps,
            settings.OLLAMA_BASE_URL,
            model,
            req.step_delay,
        )

        total_steps = len(step_log)
        successes = sum(1 for s in step_log if s.get("result", {}).get("success", False))

        return {
            "success": True,
            "goal": req.goal,
            "total_steps": total_steps,
            "successful_steps": successes,
            "step_log": step_log,
        }

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("vision-loop error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
