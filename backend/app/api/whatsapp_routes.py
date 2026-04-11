"""
api/whatsapp_routes.py -- WhatsApp Web automation endpoints.

POST /whatsapp/send   -- send a message to a contact
POST /whatsapp/read   -- read recent messages from a chat
POST /whatsapp/close  -- close the Chrome driver
GET  /whatsapp/status -- check whether the driver is running
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger("whatsapp_routes")

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


# ── Pydantic models ────────────────────────────────────────────────────────────

class SendRequest(BaseModel):
    contact: str = Field(..., description="Contact name as it appears in WhatsApp")
    message: str = Field(..., description="Message text to send")


class ReadRequest(BaseModel):
    contact: str = Field(..., description="Contact name to read messages from")
    count: int   = Field(5, ge=1, le=50, description="Number of recent messages to fetch")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/send")
async def whatsapp_send(req: SendRequest):
    """
    Send a WhatsApp message to any contact via Selenium.

    First run will open Chrome and display the QR code -- scan once and
    your session is saved permanently in backend/chrome_profile/.

    Example:
        POST /whatsapp/send
        {"contact": "Ravi", "message": "Good morning!"}
    """
    logger.info("POST /whatsapp/send | contact=%r | message=%r", req.contact, req.message[:60])

    try:
        from automation.whatsapp_automation import send_whatsapp_message

        result = await asyncio.to_thread(send_whatsapp_message, req.contact, req.message)

        if result.get("status") == "success":
            return {
                "success":     True,
                "contact":     req.contact,
                "chat_opened": result.get("chat_opened", req.contact),
                "message":     req.message,
                "detail":      "Message sent successfully via WhatsApp Web.",
            }
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "error":   result.get("error", "Unknown WhatsApp error"),
                    "contact": req.contact,
                    "hint":    "Check if the contact name matches exactly what appears in WhatsApp.",
                },
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("whatsapp/send error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/read")
async def whatsapp_read(req: ReadRequest):
    """
    Fetch recent messages from a WhatsApp chat.

    Returns a list of message objects:
      [{"sender": "you"|"them", "text": "...", "time": "..."}]

    Example:
        POST /whatsapp/read
        {"contact": "Ravi", "count": 5}
    """
    logger.info("POST /whatsapp/read | contact=%r | count=%d", req.contact, req.count)

    try:
        from automation.whatsapp_automation import read_whatsapp

        result = await asyncio.to_thread(read_whatsapp, req.contact, req.count)
        return {
            "success":  True,
            "contact":  req.contact,
            "messages": result.get("messages", []),
            "count":    result.get("count", 0),
        }

    except Exception as exc:
        logger.error("whatsapp/read error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def whatsapp_status():
    """Check whether the WhatsApp Chrome driver is currently running."""
    try:
        from automation import whatsapp_automation as wa
        driver_alive = wa._driver is not None
        if driver_alive:
            try:
                _ = wa._driver.title  # will throw if driver is dead
            except Exception:
                driver_alive = False
                wa._driver = None
        return {
            "driver_running": driver_alive,
            "profile_dir":    wa.DEFAULT_PROFILE_DIR,
            "hint": (
                "Driver is running -- Chrome window is open."
                if driver_alive
                else "Driver is not running -- will launch on next /whatsapp/send call."
            ),
        }
    except Exception as exc:
        return {"driver_running": False, "error": str(exc)}


@router.post("/close")
async def whatsapp_close():
    """Close the Chrome driver and free resources."""
    try:
        from automation.whatsapp_automation import close_driver
        await asyncio.to_thread(close_driver)
        return {"success": True, "message": "Chrome driver closed."}
    except Exception as exc:
        logger.error("whatsapp/close error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
