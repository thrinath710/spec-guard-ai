import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.models import ApiResponse

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load the embedding model up front. Otherwise the first analysis of the process pays a
    # one-off multi-second model load and looks like it has hung.
    async def _warm() -> None:
        try:
            from backend.app.ai.rag import get_embedder

            await asyncio.to_thread(get_embedder().warm_up)
            logger.info("Embedding model ready")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding warm-up failed (will load on first use): %s", exc)

    task = asyncio.create_task(_warm())
    yield
    task.cancel()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered software requirement and security assurance engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.get("/health", response_model=ApiResponse)
def root_health() -> ApiResponse:
    return ApiResponse(success=True, data={"status": "ok"})


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        },
    )
