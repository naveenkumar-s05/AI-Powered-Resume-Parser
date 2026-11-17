from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.db.init_db import create_tables
from app.routers import auth, dashboard, pages, profile, resume

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    _ = settings.upload_path
    if settings.auto_create_tables:
        try:
            await create_tables()
            logger.info("Database tables ensured")
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not ensure database tables: %s", exc)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

api_prefix = settings.api_v1_prefix
app.include_router(resume.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(profile.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(pages.router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error": {"code": exc.code, "details": exc.details},
        },
    )


def _safe_validation_errors(exc: RequestValidationError) -> list[dict]:
    return [
        {"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")}
        for err in exc.errors()
    ]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = _safe_validation_errors(exc)
    logger.warning(
        "Validation failed for %s %s: %s", request.method, request.url.path, details
    )
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation failed",
            "error": {
                "code": "VALIDATION_ERROR",
                "details": details,
            },
        },
    )


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {
        "success": True,
        "message": "ok",
        "data": {"app": settings.app_name, "env": settings.app_env},
    }
