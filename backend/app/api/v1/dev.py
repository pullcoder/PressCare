"""⚠ 개발 전용 임시 API: Supabase 준비 전 대시보드가 병상 상태를 읽는 곳.

원래 설계에서 대시보드는 Supabase bed_status·alerts 를 Realtime 구독한다 (D-009).
Supabase 가 연결되면 이 라우터와 memory_store 를 지운다.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.schemas.dev import (
    AckIn,
    DevAlert,
    DevAlertBrief,
    DevBed,
    DevBedsResponse,
    ManualPostureIn,
    ManualPostureOut,
    TimelineEvent,
    TimelineResponse,
)
from app.services.memory_store import Alert, store
from app.services.reposition import elapsed_minutes, evaluate_status

router = APIRouter(prefix="/dev", tags=["dev (임시)"])

# 시연용 가명 (실제 환자 정보 아님)
DEV_PATIENTS = {
    "301-1": "김○○",
    "301-2": "이○○",
    "301-3": "박○○",
    "301-4": "최○○",
    "301-5": "정○○",
    "301-6": "한○○",
}
LEVEL_RANK = {"critical": 2, "warning": 1}


def _settings() -> Settings:
    settings = get_settings()
    if not settings.use_memory_store:
        raise AppError("NOT_FOUND", "개발 모드에서만 쓰는 API입니다.", 404)
    return settings


def _open_alert(bed_code: str, alerts: list[Alert]) -> DevAlertBrief | None:
    open_ = [a for a in alerts if a.bed_code == bed_code and a.resolved_at is None]
    if not open_:
        return None
    top = max(open_, key=lambda a: (LEVEL_RANK.get(a.level, 0), a.id))
    return DevAlertBrief(
        id=top.id,
        level=top.level,
        acknowledged_by=top.acknowledged_by,
        acknowledged_at=top.acknowledged_at,
    )


@router.get("/beds", response_model=DevBedsResponse)
def list_beds() -> DevBedsResponse:
    settings = _settings()
    now = datetime.now(UTC)
    alerts = store.alerts(limit=500)
    beds = [
        DevBed(
            bed_code=b.bed_code,
            patient_name=DEV_PATIENTS.get(b.bed_code),
            current_posture=b.posture,
            confidence=b.confidence,
            posture_since=b.posture_since,
            status=evaluate_status(b.posture, b.posture_since, b.last_seen, now, settings),
            elapsed_min=round(elapsed_minutes(b.posture_since, now, settings.time_scale), 2),
            keypoints=b.keypoints,
            needs_check=b.needs_check,
            source=b.source,
            simulated=b.simulated,
            alert=_open_alert(b.bed_code, alerts),
        )
        for b in store.list_beds()
    ]
    return DevBedsResponse(
        time_scale=settings.time_scale,
        reposition_warning_min=settings.reposition_warning_min,
        reposition_interval_min=settings.reposition_interval_min,
        beds=beds,
    )


@router.get("/beds/{bed_code}/timeline", response_model=TimelineResponse)
def timeline(bed_code: str) -> TimelineResponse:
    """병상 하루 기록 (T3-5). 서버를 켠 뒤의 기록만 있다 (임시 저장소)."""
    settings = _settings()
    if store.get_bed(bed_code) is None:
        raise AppError("BED_NOT_FOUND", f"병상을 찾을 수 없습니다: {bed_code}", 404)
    now = datetime.now(UTC)
    raw = [e for e in store.history(bed_code) if e.posture != "unknown"]
    events: list[TimelineEvent] = []
    totals: dict[str, float] = {}
    for i, e in enumerate(raw):
        end = raw[i + 1].started_at if i + 1 < len(raw) else None
        minutes = elapsed_minutes(e.started_at, end or now, settings.time_scale)
        totals[e.posture] = round(totals.get(e.posture, 0.0) + minutes, 2)
        events.append(
            TimelineEvent(
                posture=e.posture,
                started_at=e.started_at,
                ended_at=end,
                duration_min=round(minutes, 2),
                source=e.source,
                recorded_by=e.recorded_by,
            )
        )
    return TimelineResponse(
        bed_code=bed_code,
        patient_name=DEV_PATIENTS.get(bed_code),
        time_scale=settings.time_scale,
        reposition_interval_min=settings.reposition_interval_min,
        events=events,
        totals_min=totals,
        reposition_count=max(0, len(events) - 1),
        longest_min=max((ev.duration_min for ev in events), default=0.0),
    )


@router.post("/beds/{bed_code}/postures/manual", response_model=ManualPostureOut)
def record_manual(bed_code: str, body: ManualPostureIn) -> ManualPostureOut:
    """간호사 "체위변경 완료". 원래 경로는 /beds/{bed_id}/postures/manual (로그인 필요, T2-5)."""
    _settings()
    started = body.started_at or datetime.now(UTC)
    if started.tzinfo is None:
        raise AppError("INVALID_TIME", "started_at 에 시간대(UTC)가 있어야 합니다.", 422)
    if not store.record_manual(bed_code, body.posture, started, by=body.recorded_by):
        raise AppError("BED_NOT_FOUND", f"병상을 찾을 수 없습니다: {bed_code}", 404)
    return ManualPostureOut()


def _to_dev_alert(a: Alert) -> DevAlert:
    return DevAlert(
        id=a.id,
        bed_code=a.bed_code,
        patient_name=DEV_PATIENTS.get(a.bed_code),
        level=a.level,
        created_at=a.created_at,
        acknowledged_at=a.acknowledged_at,
        acknowledged_by=a.acknowledged_by,
        resolved_at=a.resolved_at,
    )


@router.get("/alerts", response_model=list[DevAlert])
def list_alerts(limit: int = 50) -> list[DevAlert]:
    """최근 알림 (T3-6). 새 것부터."""
    _settings()
    return [_to_dev_alert(a) for a in store.alerts(limit=min(max(limit, 1), 200))]


@router.post("/alerts/{alert_id}/ack", response_model=DevAlert)
def ack_alert(alert_id: int, body: AckIn) -> DevAlert:
    """알림 확인 (API.md 5장의 임시판). 누가 언제 확인했는지 남긴다."""
    _settings()
    name = body.acknowledged_by.strip()[:20] or "간호사"
    alert = store.ack_alert(alert_id, name, datetime.now(UTC))
    if alert is None:
        raise AppError("ALERT_NOT_FOUND", f"알림을 찾을 수 없습니다: {alert_id}", 404)
    return _to_dev_alert(alert)
