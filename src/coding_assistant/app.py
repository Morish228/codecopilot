import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from coding_assistant.api.router import api_router
from coding_assistant.api.routes.metrics_route import router as metrics_router
from coding_assistant.config import get_settings
from coding_assistant.db.session import init_db
from coding_assistant.routing.credentials import configure_litellm_credentials
from coding_assistant.observability import setup_observability
from coding_assistant.observability.middleware import ObservabilityMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    configure_litellm_credentials(settings)
    setup_observability()
    await init_db()
    logger.info("Database initialized")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Coding Assistant API",
        version="0.1.0",
        description="Phase 1 core runtime — LangGraph orchestration with structured tools",
        lifespan=lifespan,
    )
    
    # Enable CORS for web UI and external clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(ObservabilityMiddleware)
    app.include_router(metrics_router)
    app.include_router(api_router)
    
    # Serve web UI
    web_dir = Path(__file__).parent.parent.parent / "web"
    if not web_dir.exists():
        web_dir = Path.cwd() / "web"
    if web_dir.exists():
        # Mount static files
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
        
        # Serve index.html at root
        @app.get("/")
        async def serve_web_ui():
            index_file = web_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file), media_type="text/html")
            return {"message": "CodeCopilot API - Open http://127.0.0.1:8000/docs for API docs"}
    
    return app
