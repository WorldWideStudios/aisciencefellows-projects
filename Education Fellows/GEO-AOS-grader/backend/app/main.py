import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api import analyze, health, report
from app.config import settings
from app.middleware import RateLimitMiddleware, RequestIdMiddleware


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


def _configure_logging() -> None:
    logger.remove()
    logger.configure(extra={"request_id": "-"})
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
            "| <level>{level: <8}</level> "
            "| <cyan>{extra[request_id]}</cyan> "
            "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
            "- <level>{message}</level>"
        ),
    )


_configure_logging()


app = FastAPI(title="AEO Grader", version="0.1.0", default_response_class=UTF8JSONResponse)

# middleware: rate limit OUTSIDE request_id, чтобы 429 уходил без логирования
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(report.router, prefix="/api")


@app.on_event("startup")
async def startup() -> None:
    logger.info("AEO Grader backend started")
