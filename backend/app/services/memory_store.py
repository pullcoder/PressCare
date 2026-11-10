"""⚠ 임시 저장소: Supabase(T0-3, T2-1) 준비 전 개발·시연용.

서버 메모리에만 있으므로 서버를 끄면 사라진다. Supabase 가 연결되면
bed_status / posture_events 테이블로 바꾸고 이 파일은 지운다.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime

from app.core.postures import Posture

KNOWN_POSTURES = ("supine", "left_lateral", "right_lateral", "sitting")


@dataclass
class BedState:
    bed_code: str
    posture: Posture  # 마지막으로 확인된 자세 (인식이 잠깐 안 돼도 유지)
    confidence: float
    posture_since: datetime  # 그 자세가 시작된 시각 (타이머 기준)
    last_seen: datetime  # 마지막으로 엣지에서 무엇이든 받은 시각 (offline 판단)
    keypoints: list[list[float]] | None = None
    needs_check: bool = False  # 지금 인식이 안 됨(이불·어둠 등) → 화면에 "확인 필요"
    source: str = "edge"  # edge | manual


def apply_posture(
    prev: BedState | None,
    bed_code: str,
    posture: Posture,
    confidence: float,
    started_at: datetime,
    keypoints: list[list[float]] | None,
    now: datetime,
) -> BedState:
    """자세 확정 이벤트를 병상 상태에 반영한다.

    - unknown(인식 안 됨): 마지막 자세와 타이머를 그대로 두고 "확인 필요"만 표시한다.
      이불·어둠 때문에 타이머가 0으로 돌아가면 실제로는 오래 누워 있는데도 알림이 늦어진다.
    - 인식이 돌아왔는데 같은 자세면: 타이머를 이어 간다 (자세가 바뀐 게 아님).
    - 다른 자세 또는 absent(자리 비움): 새 타이머를 시작한다.
    """
    known = prev is not None and prev.posture in KNOWN_POSTURES
    if posture == "unknown" and known:
        assert prev is not None
        return BedState(
            bed_code,
            prev.posture,
            prev.confidence,
            prev.posture_since,
            now,
            prev.keypoints,
            needs_check=True,
            source=prev.source,
        )
    if known and prev is not None and prev.needs_check and posture == prev.posture:
        return BedState(
            bed_code, posture, confidence, prev.posture_since, now, keypoints, source=prev.source
        )
    return BedState(bed_code, posture, confidence, started_at, now, keypoints)


class MemoryBedStore:
    def __init__(self) -> None:
        self._beds: dict[str, BedState] = {}
        self._event_id = 0
        self._lock = threading.Lock()

    def record_posture(
        self,
        bed_code: str,
        posture: Posture,
        confidence: float,
        started_at: datetime,
        keypoints: list[list[float]] | None,
        now: datetime,
    ) -> int:
        with self._lock:
            self._event_id += 1
            self._beds[bed_code] = apply_posture(
                self._beds.get(bed_code), bed_code, posture, confidence, started_at, keypoints, now
            )
            return self._event_id

    def record_manual(self, bed_code: str, posture: Posture, started_at: datetime) -> bool:
        """간호사가 체위변경을 기록 (API.md 4장). 병상이 없으면 False."""
        with self._lock:
            bed = self._beds.get(bed_code)
            if bed is None:
                return False
            bed.posture = posture
            bed.posture_since = started_at
            bed.confidence = 1.0
            bed.needs_check = False
            bed.source = "manual"
            return True

    def heartbeat(self, bed_code: str, posture: Posture, confidence: float, now: datetime) -> None:
        with self._lock:
            bed = self._beds.get(bed_code)
            if bed is None:
                # 아직 확정된 자세가 없는 새 병상: 화면에 나타나도록 만든다
                self._beds[bed_code] = BedState(bed_code, posture, confidence, now, now)
            else:
                bed.last_seen = now

    def list_beds(self) -> list[BedState]:
        with self._lock:
            return sorted(
                (BedState(**vars(b)) for b in self._beds.values()), key=lambda b: b.bed_code
            )

    def clear(self) -> None:
        with self._lock:
            self._beds.clear()


store = MemoryBedStore()
