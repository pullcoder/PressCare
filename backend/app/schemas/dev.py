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


class DevBedsResponse(BaseModel):
    time_scale: float
    reposition_warning_min: int
    reposition_interval_min: int
    beds: list[DevBed]
