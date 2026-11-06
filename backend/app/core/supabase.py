"""Supabase 연결 (D-009, D-010).

backend는 secret(service role) 키로 Supabase에 쓴다. 이 키는 RLS를 무시하므로
backend 밖(frontend, 로그, 응답)으로 절대 내보내지 않는다. (AGENTS.md 4-2)
"""

import logging
from functools import lru_cache
from typing import Literal

import httpx
from supabase import Client, create_client

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

PING_TIMEOUT_SEC = 3.0

SupabaseState = Literal["connected", "unreachable", "not_configured"]


@lru_cache
def get_supabase() -> Client:
    """service key로 만든 Supabase 클라이언트 (프로세스당 1개)."""
    settings = get_settings()
    if not settings.supabase_configured:
        raise AppError(
            "SUPABASE_NOT_CONFIGURED",
            ".env에 SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 넣어주세요.",
            status=503,
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def check_connection() -> SupabaseState:
    """Supabase Auth 헬스 엔드포인트로 연결만 확인한다. 데이터는 읽지 않는다."""
    settings = get_settings()
    if not settings.supabase_configured:
        return "not_configured"
    url = settings.supabase_url.rstrip("/") + "/auth/v1/health"
    try:
        response = httpx.get(
            url,
            headers={"apikey": settings.supabase_service_role_key},
            timeout=PING_TIMEOUT_SEC,
        )
    except httpx.HTTPError as exc:
        logger.warning("Supabase 연결 실패: %s", exc.__class__.__name__)
        return "unreachable"
    return "connected" if response.status_code == 200 else "unreachable"
