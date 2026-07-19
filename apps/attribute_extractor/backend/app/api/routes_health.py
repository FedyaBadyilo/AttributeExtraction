"""Health endpoints."""

from fastapi import APIRouter

from backend.app.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "sqlite_path": str(settings.sqlite_path),
    }
