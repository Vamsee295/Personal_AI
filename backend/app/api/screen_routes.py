"""
api/screen_routes.py – Dedicated screen AI endpoint that combines capture + OCR + AI analysis.
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
from typing import List

from app.services.ai_service import ai_service
from app.utils.logger import get_logger

logger = get_logger("screen_routes")

router = APIRouter(prefix="/api/screen", tags=["Screen AI"])

# Active websocket connections for live insights
active_connections: List[WebSocket] = []

# Global state to prevent redundant error explanations
last_error_text = ""

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
        import asyncio

        # Step 1: Capture (run in threadpool to avoid blocking event loop)
        image_bytes = await asyncio.to_thread(screen_agent.capture_screen)

        # Step 2: OCR (also in threadpool)
        screen_text = await asyncio.to_thread(screen_agent.extract_text, image_bytes)

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
        text = await asyncio.to_thread(screen_agent.extract_text)
        return {"text": text, "success": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.websocket("/live-insights")
async def websocket_live_insights(websocket: WebSocket):
    """WebSocket for broadcasting auto-detected screen errors and explanations."""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("Client connected to live-insights. Total: %d", len(active_connections))
    try:
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("Client disconnected from live-insights.")


async def screen_monitoring_loop():
    """Background task that runs every few seconds to check for errors."""
    global last_error_text
    logger.info("Started background screen monitoring loop.")
    
    # Wait a bit before starting
    await asyncio.sleep(5)
    
    from app.agents.screen_agent import screen_agent
    
    while True:
        try:
            # Only run if there are connected clients
            if active_connections:
                logger.debug("Checking screen for errors...")
                
                # Detect errors (runs in threadpool)
                error_text = await asyncio.to_thread(screen_agent.detect_errors)
                
                if error_text and error_text != last_error_text:
                    logger.info("New screen error detected! Querying AI...")
                    last_error_text = error_text
                    
                    # Notify frontend we are analyzing
                    for conn in active_connections:
                        try:
                            await conn.send_json({"type": "status", "message": "Error detected, analysing..."})
                        except:
                            pass
                            
                    prompt = (
                        f"The following error/exception was detected on my screen:\n\n"
                        f"---\n{error_text[:2000]}\n---\n\n"
                        f"Explain what this error means and provide a concise, actionable fix."
                    )

                    analysis = await ai_service.chat(
                        message=prompt,
                        history=[ChatMessage(role="system", content=_SCREEN_SYSTEM)],
                        model="qwen2.5-coder:7b",
                    )
                    
                    # Broadcast to all connected clients
                    for conn in active_connections:
                        try:
                            await conn.send_json({
                                "type": "insight",
                                "error_text": error_text,
                                "analysis": analysis
                            })
                        except Exception as e:
                            logger.error("Failed to send to client: %s", e)
                            
        except Exception as e:
            logger.error("Screen monitoring loop error: %s", e)
            
        # Run every 5 seconds
        await asyncio.sleep(5)

