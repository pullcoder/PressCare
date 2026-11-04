from fastapi import APIRouter

from app.core import supabase
from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """서버와 Supabase 연결 상태. Supabase가 안 돼도 서버 자체는 응답한다."""
    return HealthResponse(
        status="ok",
        app_env=get_settings().app_env,
        supabase=supabase.check_connection(),
    )
