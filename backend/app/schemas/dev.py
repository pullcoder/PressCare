from datetime import datetime

from pydantic import BaseModel

from app.core.postures import BedStatus, Posture


class DevBed(BaseModel):
    """개발용 임시 병상 상태 (Supabase bed_status 와 같은 의미의 필드)."""

    bed_code: str
    current_posture: Posture
    confidence: float
    posture_since: datetime
    status: BedStatus
    elapsed_min: float  # DEMO_TIME_SCALE 반영한 유지 시간 (분)
    keypoints: list[list[float]] | None = None
    needs_check: bool = False  # 인식이 안 되는 중 (마지막 자세·타이머는 유지)
    source: str = "edge"  # edge | manual


class ManualPostureIn(BaseModel):
    """간호사 수동 기록 (API.md 4장). started_at 을 비우면 지금."""

    posture: Posture
    started_at: datetime | None = None
    note: str | None = None


class ManualPostureOut(BaseModel):
    ok: bool = True


class DevBedsResponse(BaseModel):
    time_scale: float
    reposition_warning_min: int
    reposition_interval_min: int
    beds: list[DevBed]
