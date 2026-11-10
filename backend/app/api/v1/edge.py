"""엣지(병상 PC) → backend (API.md 3장).

지금은 Supabase 준비 전이라 임시 메모리 저장소(dev 모드)로만 동작한다.
Supabase 연결 후에는 기기 토큰 해시로 병상을 찾고 posture_events / bed_status 에 저장한다 (T2-3).
"""

import hmac
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Header

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.edge import HeartbeatIn, HeartbeatOut, PostureEventIn, PostureEventOut
from app.services.memory_store import store

router = APIRouter(prefix="/edge", tags=["edge"])
logger = logging.getLogger(__name__)


def resolve_bed(device_token: str, dev_bed_code: str | None) -> str:
    settings = get_settings()
    if not settings.use_memory_store:
        raise AppError("NOT_IMPLEMENTED", "Supabase 저장은 아직 구현 전입니다 (T2-3).", 501)
    expected = settings.edge_device_token
    if expected and not hmac.compare_digest(device_token.encode(), expected.encode()):
        raise AppError("INVALID_DEVICE_TOKEN", "기기 토큰이 올바르지 않습니다.", 401)
    if not dev_bed_code:
        raise AppError(
            "BED_CODE_REQUIRED", "개발 모드에서는 X-Dev-Bed-Code 헤더가 필요합니다.", 400
        )
    return dev_bed_code


DeviceToken = Annotated[str, Header(alias="X-Device-Token")]
DevBedCode = Annotated[str | None, Header(alias="X-Dev-Bed-Code")]


@router.post("/posture-events", response_model=PostureEventOut, status_code=201)
def post_posture_event(
    body: PostureEventIn, x_device_token: DeviceToken = "", x_dev_bed_code: DevBedCode = None
) -> PostureEventOut:
    bed = resolve_bed(x_device_token, x_dev_bed_code)
    event_id = store.record_posture(
        bed, body.posture, body.confidence, body.started_at, body.keypoints, datetime.now(UTC)
    )
    logger.info("자세 확정 bed=%s posture=%s", bed, body.posture)
    return PostureEventOut(event_id=event_id)


@router.post("/heartbeat", response_model=HeartbeatOut)
def post_heartbeat(
    body: HeartbeatIn, x_device_token: DeviceToken = "", x_dev_bed_code: DevBedCode = None
) -> HeartbeatOut:
    bed = resolve_bed(x_device_token, x_dev_bed_code)
    store.heartbeat(bed, body.current_posture, body.confidence, datetime.now(UTC))
    return HeartbeatOut()
