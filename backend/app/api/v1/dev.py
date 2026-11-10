"""⚠ 개발 전용 임시 API: Supabase 준비 전 대시보드가 병상 상태를 읽는 곳.

원래 설계에서 대시보드는 Supabase bed_status 를 Realtime 구독한다 (D-009).
Supabase 가 연결되면 이 라우터와 memory_store 를 지운다.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.dev import DevBed, DevBedsResponse, ManualPostureIn, ManualPostureOut
from app.services.memory_store import store
from app.services.reposition import elapsed_minutes, evaluate_status

router = APIRouter(prefix="/dev", tags=["dev (임시)"])


@router.get("/beds", response_model=DevBedsResponse)
def list_beds() -> DevBedsResponse:
    settings = get_settings()
    if not settings.use_memory_store:
        raise AppError("NOT_FOUND", "개발 모드에서만 쓰는 API입니다.", 404)
    now = datetime.now(UTC)
    beds = [
        DevBed(
            bed_code=b.bed_code,
            current_posture=b.posture,
            confidence=b.confidence,
            posture_since=b.posture_since,
            status=evaluate_status(b.posture, b.posture_since, b.last_seen, now, settings),
            elapsed_min=round(elapsed_minutes(b.posture_since, now, settings.time_scale), 2),
            keypoints=b.keypoints,
            needs_check=b.needs_check,
            source=b.source,
        )
        for b in store.list_beds()
    ]
    return DevBedsResponse(
        time_scale=settings.time_scale,
        reposition_warning_min=settings.reposition_warning_min,
        reposition_interval_min=settings.reposition_interval_min,
        beds=beds,
    )


@router.post("/beds/{bed_code}/postures/manual", response_model=ManualPostureOut)
def record_manual(bed_code: str, body: ManualPostureIn) -> ManualPostureOut:
    """간호사 "체위변경 완료". 원래 경로는 /beds/{bed_id}/postures/manual (로그인 필요, T2-5)."""
    settings = get_settings()
    if not settings.use_memory_store:
        raise AppError("NOT_FOUND", "개발 모드에서만 쓰는 API입니다.", 404)
    started = body.started_at or datetime.now(UTC)
    if started.tzinfo is None:
        raise AppError("INVALID_TIME", "started_at 에 시간대(UTC)가 있어야 합니다.", 422)
    if not store.record_manual(bed_code, body.posture, started):
        raise AppError("BED_NOT_FOUND", f"병상을 찾을 수 없습니다: {bed_code}", 404)
    return ManualPostureOut()
