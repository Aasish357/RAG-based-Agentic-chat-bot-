"""
FastAPI application entry point for Jahiv - Fully local Agentic RAG workspace.
"""

from contextlib import asynccontextmanager
import logging
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jahiv")


try:
    from app.db.session import init_db
except ImportError:
    init_db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Jahiv backend starting...")
    if init_db is not None:
        try:
            await init_db()
            logger.info("Database initialized successfully.")
        except Exception as exc:
            logger.warning(f"Database initialization failed: {exc}")
    yield
    logger.info("Jahiv backend shutting down...")


app = FastAPI(
    title="Jahiv",
    description="Fully local Agentic RAG workspace",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers from api module if available
try:
    from app.api.routes import router as api_routes
    if getattr(api_routes, "prefix", None):
        app.include_router(api_routes)
    else:
        app.include_router(api_routes, prefix="/api")
except ImportError:
    try:
        from app.api import router as api_router
        app.include_router(api_router)
    except ImportError:
        logger.info("API routes not yet implemented or imported.")


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint verifying application status."""
    return {"name": "Jahiv", "status": "running"}


@app.get("/health")
@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """
    Check Ollama service reachability and retrieve available models.
    Returns:
        {"ollama": bool, "models": List[str]}
    """
    ollama_ok = False
    model_names: List[str] = []

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                ollama_ok = True
                models_data = data.get("models", [])
                model_names = [
                    m.get("name", "") for m in models_data if isinstance(m, dict) and m.get("name")
                ]
    except Exception as exc:
        logger.warning(f"Ollama health check failed: {exc}")
        ollama_ok = False
        model_names = []

    return {"ollama": ollama_ok, "models": model_names}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
