from datetime import datetime

from pydantic import BaseModel

from app.core.postures import BedStatus, Posture


class DevAlertBrief(BaseModel):
    id: int
    level: BedStatus
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None


class DevBed(BaseModel):
    """개발용 임시 병상 상태 (Supabase bed_status 와 같은 의미의 필드)."""

    bed_code: str
    patient_name: str | None = None  # 가명/이니셜만 (CONVENTIONS 6장)
    current_posture: Posture
    confidence: float
    posture_since: datetime
    status: BedStatus
    elapsed_min: float  # DEMO_TIME_SCALE 반영한 유지 시간 (분)
    keypoints: list[list[float]] | None = None
    needs_check: bool = False  # 인식이 안 되는 중 (마지막 자세·타이머는 유지)
    source: str = "edge"  # edge | manual
    simulated: bool = False  # 시연용 가짜 병상
    alert: DevAlertBrief | None = None  # 지금 열려 있는(해제 안 된) 가장 높은 단계 알림


class DevBedsResponse(BaseModel):
    time_scale: float
    reposition_warning_min: int
    reposition_interval_min: int
    beds: list[DevBed]


class ManualPostureIn(BaseModel):
    """간호사 수동 기록 (API.md 4장). started_at 을 비우면 지금."""

    posture: Posture
    started_at: datetime | None = None
    note: str | None = None
    recorded_by: str | None = None


class ManualPostureOut(BaseModel):
    ok: bool = True


class TimelineEvent(BaseModel):
    posture: Posture
    started_at: datetime
    ended_at: datetime | None  # 아직 이어지는 중이면 None
    duration_min: float  # 가속 반영 (분)
    source: str
    recorded_by: str | None = None


class TimelineResponse(BaseModel):
    bed_code: str
    patient_name: str | None
    time_scale: float
    reposition_interval_min: int
    events: list[TimelineEvent]
    totals_min: dict[str, float]  # 자세별 누적 유지 시간 (3D 히트맵 계산용)
    reposition_count: int  # 자세가 바뀐 횟수
    longest_min: float


class DevAlert(BaseModel):
    id: int
    bed_code: str
    patient_name: str | None
    level: BedStatus
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None


class AckIn(BaseModel):
    acknowledged_by: str = "간호사"
