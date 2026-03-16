"""
run.py – Entry point for the Vamsee AI backend server.
Run with:  python run.py
"""

import uvicorn
from app.utils.logger import get_logger

logger = get_logger("runner")

if __name__ == "__main__":
    logger.info("🚀  Starting Vamsee AI Backend …")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # hot-reload during development
        log_level="info",
    )
