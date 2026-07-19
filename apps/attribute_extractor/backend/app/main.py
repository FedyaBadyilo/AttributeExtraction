"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes_files import router as files_router
from backend.app.api.routes_health import router as health_router
from backend.app.api.routes_processing import router as processing_router
from backend.app.api.routes_tasks import router as tasks_router
from backend.app.api.routes_validation import router as validation_router
from backend.app.constants import APP_TITLE, APP_VERSION
from backend.app.db import init_db
from backend.app.errors import ApiError, api_error_handler
from backend.app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.backend_log_level.upper())
    init_db(settings)
    yield


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(files_router)
app.include_router(validation_router)
app.include_router(processing_router)
