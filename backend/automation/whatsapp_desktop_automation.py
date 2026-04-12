"""
automation/whatsapp_desktop_automation.py -- PyAutoGUI-powered WhatsApp Desktop controller.

This module uses UI automation to control the native Windows WhatsApp Desktop app.
The screen must be unlocked and the application window must not be interrupted during the process.
"""

import time
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("whatsapp_desktop_automation")

# Constant delay to wait for WhatsApp Desktop to open and become active
APP_LOAD_DELAY = 5.0

def open_whatsapp() -> bool:
    """
    Attempts to open the WhatsApp Desktop app installed from the Microsoft Store.
    Returns True if successful, False otherwise.
    """
    try:
        # Solution 1: Microsoft Store App Path
        logger.info("Attempting to open WhatsApp Desktop (Store app)")
        subprocess.Popen("explorer shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App", shell=True)
        return True
    except Exception as e:
        logger.error("Failed to open WhatsApp (Store App): %s", e)
        try:
            # Fallback for manually installed executable
            import os
            logger.info("Attempting fallback path for WhatsApp Desktop")
            fallback_path = os.path.expanduser("~\\AppData\\Local\\WhatsApp\\WhatsApp.exe")
            subprocess.Popen(fallback_path)
            return True
        except Exception as fallback_e:
            logger.error("Failed to open WhatsApp (Fallback): %s", fallback_e)
            return False

def send_whatsapp_message(contact_name: str, message: str) -> Dict[str, Any]:
    """
    Opens WhatsApp Desktop and uses keyboard shortcuts (pyautogui) to send a message.
    """
    import pyautogui
    
    logger.info("Starting Desktop automation to send message to: %s", contact_name)

    # 1. Open WhatsApp
    success = open_whatsapp()
    if not success:
        return {"status": "error", "error": "Failed to launch WhatsApp Desktop application."}
    
    # 2. Wait for app to load and become active
    logger.info("Waiting %.1f seconds for app to load...", APP_LOAD_DELAY)
    time.sleep(APP_LOAD_DELAY)
    
    try:
        # 3. Focus search box (Ctrl+F)
        logger.info("Triggering search (Ctrl+F)")
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(1.0)
        
        # 4. Type contact name
        logger.info("Typing contact name")
        pyautogui.write(contact_name)
        time.sleep(2.0) # Wait for search results
        
        # Select first result
        logger.info("Pressing enter to select contact")
        pyautogui.press('enter')
        time.sleep(1.0) # wait for chat to load
        
        # 5. Type and send the message
        logger.info("Typing message")
        pyautogui.write(message)
        time.sleep(0.5)
        
        logger.info("Sending message (Enter)")
        pyautogui.press('enter')
        
        logger.info("Message automation complete")
        return {
            "status": "success",
            "contact": contact_name,
            "message": message
        }
        
    except pyautogui.FailSafeException:
        logger.error("PyAutoGUI Failsafe triggered! Process aborted by user mouse movement.")
        return {"status": "error", "error": "Automation aborted by mouse movement (FailSafe)."}
    except Exception as e:
        logger.exception("Unexpected error during UI automation.")
        return {"status": "error", "error": str(e)}

def read_whatsapp(contact_name: str, count: int = 5) -> Dict[str, Any]:
     """
     Placeholder for reading messages natively.
     Reading text via PyAutoGUI is generally not feasible directly without OCR.
     """
     logger.warning("read_whatsapp is not supported with pure PyAutoGUI Desktop automation.")
     return {
         "status": "error",
         "error": "Reading messages requires computer vision/OCR and is unsupported in the current desktop implementation.",
         "contact": contact_name
     }
