"""⚠ 임시 저장소: Supabase(T0-3, T2-1) 준비 전 개발·시연용.

서버 메모리에만 있으므로 서버를 끄면 사라진다. Supabase 가 연결되면
bed_status / posture_events 테이블로 바꾸고 이 파일은 지운다.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime

from app.core.postures import Posture


@dataclass
class BedState:
    bed_code: str
    posture: Posture
    confidence: float
    posture_since: datetime
    last_seen: datetime  # 마지막으로 엣지에서 무엇이든 받은 시각 (offline 판단)
    keypoints: list[list[float]] | None = None


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
            self._beds[bed_code] = BedState(
                bed_code, posture, confidence, started_at, now, keypoints
            )
            return self._event_id

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
