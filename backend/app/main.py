"""
app/main.py – FastAPI application factory with all routes and middleware.
"""

from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import chat_routes, file_routes, terminal_routes, agent_routes, system_routes, voice_routes, screen_routes, executor_routes, vision_routes, whatsapp_routes, health_routes, memory_routes, voice_ws_routes
from app.utils.logger import get_logger

logger = get_logger("main")


# ── Application lifecycle ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown log hooks."""
    import asyncio
    from app.api.screen_routes import screen_monitoring_loop

    logger.info("═══ Ultron Backend v%s starting ═══", settings.APP_VERSION)
    logger.info("Ollama URL  : %s", settings.OLLAMA_BASE_URL)
    logger.info("Default model: %s", settings.DEFAULT_MODEL)
    
    # Start the screen monitoring background task
    screen_task = asyncio.create_task(screen_monitoring_loop())
    
    yield
    
    # Cancel the background task on shutdown
    screen_task.cancel()
    logger.info("═══ Ultron Backend shutting down ═══")


# ── App instance ───────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend API for Ultron – a local AI-powered coding assistant. "
        "Provides AI chat, code generation, file management, terminal execution, "
        "and an autonomous agent engine powered by Ollama."
    ),
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ───────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s: %s", request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "detail": str(exc)},
    )

# ── Routers ────────────────────────────────────────────────────────
app.include_router(chat_routes.router)
app.include_router(file_routes.router)
app.include_router(terminal_routes.router)
app.include_router(agent_routes.router)
app.include_router(system_routes.router)
app.include_router(voice_routes.router)
app.include_router(screen_routes.router)
app.include_router(executor_routes.router)
app.include_router(vision_routes.router)
app.include_router(whatsapp_routes.router)
app.include_router(health_routes.router)
app.include_router(memory_routes.router)
app.include_router(voice_ws_routes.router)


# ── Root ───────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
    }
