"""병상 상태 판단 (체위변경 기준, D-007).

경과 시간은 저장하지 않고 `지금 - posture_since` 로 계산한다. (ARCHITECTURE 2장)
DEMO_TIME_SCALE 은 시연 전용 가속 배수이며 production 에서는 항상 1이다.
"""

from __future__ import annotations

from datetime import datetime

from app.core.config import Settings
from app.core.postures import BedStatus, Posture


def elapsed_minutes(posture_since: datetime, now: datetime, time_scale: float) -> float:
    """가속 배수를 반영한 자세 유지 시간 (분)."""
    seconds = max(0.0, (now - posture_since).total_seconds())
    return seconds / 60 * time_scale


def evaluate_status(
    posture: Posture,
    posture_since: datetime,
    last_seen: datetime,
    now: datetime,
    settings: Settings,
) -> BedStatus:
    # offline 은 실제 시간 기준 (가속하지 않음)
    if (now - last_seen).total_seconds() > settings.edge_offline_sec:
        return "offline"
    if posture in ("unknown", "absent"):
        return "unknown"  # 자세를 알 수 없거나 자리에 없음 → 간호사 확인 필요
    minutes = elapsed_minutes(posture_since, now, settings.time_scale)
    if minutes >= settings.reposition_interval_min:
        return "critical"
    if minutes >= settings.reposition_warning_min:
        return "warning"
    return "ok"
