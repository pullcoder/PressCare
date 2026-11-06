from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.postures import Posture


class PostureEventIn(BaseModel):
    """엣지가 자세를 확정했을 때 보내는 값 (API.md 3장). 영상·이미지는 받지 않는다."""

    posture: Posture
    confidence: float = Field(ge=0, le=1)
    started_at: datetime
    keypoints: list[list[float]] | None = None  # [x, y, visibility] × 33, 선택

    @field_validator("keypoints")
    @classmethod
    def check_keypoints(cls, v: list[list[float]] | None) -> list[list[float]] | None:
        if v is not None and (len(v) != 33 or any(len(p) != 3 for p in v)):
            raise ValueError("keypoints 는 [x, y, visibility] 33개여야 합니다")
        return v

    @field_validator("started_at")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("started_at 에 시간대(UTC, 끝에 Z)가 있어야 합니다")
        return v


class PostureEventOut(BaseModel):
    event_id: int


class HeartbeatIn(BaseModel):
    current_posture: Posture
    confidence: float = Field(ge=0, le=1)
    fps: float = Field(ge=0)


class HeartbeatOut(BaseModel):
    ok: bool = True
