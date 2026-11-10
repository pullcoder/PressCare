"""⚠ 임시 저장소: Supabase(T0-3, T2-1) 준비 전 개발·시연용.

서버 메모리에만 있으므로 서버를 끄면 사라진다. Supabase 가 연결되면
bed_status / posture_events / alerts 테이블로 바꾸고 이 파일은 지운다.
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from app.core.config import Settings
from app.core.postures import BedStatus, Posture
from app.services.reposition import elapsed_minutes, evaluate_status

KNOWN_POSTURES = ("supine", "left_lateral", "right_lateral", "sitting")
# 시뮬레이션 병상의 간호사가 돌려 눕히는 순서 (실무: 좌측위 → 앙와위 → 우측위)
TURN_ORDER: tuple[Posture, ...] = ("left_lateral", "supine", "right_lateral")


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
    simulated: bool = False  # 시연용 가짜 병상 (DEV_FAKE_BEDS)


@dataclass
class PostureEvent:
    """자세가 바뀐 기록 1건 (posture_events 테이블과 같은 의미)."""

    posture: Posture
    started_at: datetime
    source: str  # edge | manual
    recorded_by: str | None = None


@dataclass
class Alert:
    id: int
    bed_code: str
    level: BedStatus  # warning | critical
    posture_since: datetime  # 어느 자세 구간의 알림인지 (같은 구간에 같은 단계는 한 번만)
    created_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None  # 체위가 바뀌어 자동 해제된 시각


@dataclass
class _SimPlan:
    nurse_delay_min: float  # critical 뒤 간호사가 오기까지 (가속 시간, 분)
    nurse: str
    offline: bool = False
    turn_index: int = 0


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
        return replace(prev, last_seen=now, needs_check=True)
    if known and prev is not None and prev.needs_check and posture == prev.posture:
        return replace(
            prev, confidence=confidence, last_seen=now, keypoints=keypoints, needs_check=False
        )
    simulated = prev.simulated if prev else False
    return BedState(bed_code, posture, confidence, started_at, now, keypoints, simulated=simulated)


@dataclass
class MemoryBedStore:
    _beds: dict[str, BedState] = field(default_factory=dict)
    _history: dict[str, list[PostureEvent]] = field(default_factory=dict)
    _alerts: list[Alert] = field(default_factory=list)
    _sim: dict[str, _SimPlan] = field(default_factory=dict)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))
    _alert_ids: itertools.count = field(default_factory=lambda: itertools.count(1))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ----- 내부 -----
    def _set(self, new: BedState, source: str, recorded_by: str | None, now: datetime) -> None:
        prev = self._beds.get(new.bed_code)
        self._beds[new.bed_code] = new
        if prev is None or new.posture_since != prev.posture_since or new.posture != prev.posture:
            self._history.setdefault(new.bed_code, []).append(
                PostureEvent(new.posture, new.posture_since, source, recorded_by)
            )
            # 체위가 바뀌면 이전 자세 구간의 알림은 자동 해제
            for a in self._alerts:
                if a.bed_code == new.bed_code and a.resolved_at is None:
                    a.resolved_at = now

    # ----- 엣지 -----
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
            new = apply_posture(
                self._beds.get(bed_code), bed_code, posture, confidence, started_at, keypoints, now
            )
            self._set(new, "edge", None, now)
            return next(self._ids)

    def heartbeat(self, bed_code: str, posture: Posture, confidence: float, now: datetime) -> None:
        with self._lock:
            bed = self._beds.get(bed_code)
            if bed is None:
                # 아직 확정된 자세가 없는 새 병상: 화면에 나타나도록 만든다
                self._set(BedState(bed_code, posture, confidence, now, now), "edge", None, now)
            else:
                bed.last_seen = now

    # ----- 간호사 -----
    def record_manual(
        self, bed_code: str, posture: Posture, started_at: datetime, by: str | None = None
    ) -> bool:
        """간호사가 체위변경을 기록 (API.md 4장). 병상이 없으면 False."""
        with self._lock:
            bed = self._beds.get(bed_code)
            if bed is None:
                return False
            new = replace(
                bed,
                posture=posture,
                posture_since=started_at,
                confidence=1.0,
                needs_check=False,
                source="manual",
            )
            self._set(new, "manual", by, started_at)
            return True

    def ack_alert(self, alert_id: int, by: str, now: datetime) -> Alert | None:
        with self._lock:
            for a in self._alerts:
                if a.id == alert_id:
                    if a.acknowledged_at is None:
                        a.acknowledged_at, a.acknowledged_by = now, by
                    return replace(a)
            return None

    # ----- 알림 판단 루프 (T3-1, ALERT_CHECK_SEC 마다) -----
    def check_alerts(self, now: datetime, settings: Settings) -> list[Alert]:
        """warning·critical 에 들어선 병상마다 알림을 한 번씩 만들고, 새 알림을 돌려준다."""
        created: list[Alert] = []
        with self._lock:
            for bed in self._beds.values():
                status = evaluate_status(
                    bed.posture, bed.posture_since, bed.last_seen, now, settings
                )
                if status not in ("warning", "critical"):
                    continue
                exists = any(
                    a.bed_code == bed.bed_code
                    and a.level == status
                    and a.posture_since == bed.posture_since
                    for a in self._alerts
                )
                if not exists:
                    alert = Alert(
                        next(self._alert_ids), bed.bed_code, status, bed.posture_since, now
                    )
                    self._alerts.append(alert)
                    created.append(alert)
        return created

    # ----- 시연용 가짜 병상 -----
    def seed_fake_beds(self, count: int, now: datetime, settings: Settings) -> None:
        """실제 카메라 병상(301-1) 옆에 가짜 병상을 채워 6인실처럼 보이게 한다."""
        scale = settings.time_scale
        interval = settings.reposition_interval_min

        def ago(minutes: float) -> datetime:  # 가속 시간(분) → 실제 시각
            return now - timedelta(seconds=minutes * 60 / scale)

        # (병상, 현재 자세, 경과 비율, 인식 불가, 연결 끊김, 담당 간호사)
        plans = [
            ("301-2", "left_lateral", 0.30, False, False, "김간호사"),
            ("301-3", "right_lateral", 0.85, False, False, "이간호사"),
            ("301-4", "supine", 0.55, True, False, "박간호사"),
            ("301-5", "sitting", 0.10, False, False, "김간호사"),
            ("301-6", "supine", 0.65, False, True, "이간호사"),
        ][:count]
        with self._lock:
            for i, (code, posture, ratio, needs_check, offline, nurse) in enumerate(plans):
                since = ago(interval * ratio)
                # 오늘 앞선 기록 3건 (각 자세를 interval 근처만큼 유지했다고 가정)
                t = since
                history: list[PostureEvent] = []
                for k, p in enumerate((TURN_ORDER * 2)[i : i + 3]):
                    t = t - timedelta(seconds=interval * (0.9 + 0.05 * k) * 60 / scale)
                    history.append(PostureEvent(p, t, "manual", nurse))
                history.reverse()
                history.append(PostureEvent(posture, since, "edge"))  # type: ignore[arg-type]
                self._history[code] = history
                last_seen = (
                    now - timedelta(seconds=settings.edge_offline_sec + 30) if offline else now
                )
                self._beds[code] = BedState(
                    code,
                    posture,
                    0.9,
                    since,
                    last_seen,  # type: ignore[arg-type]
                    needs_check=needs_check,
                    simulated=True,
                )
                self._sim[code] = _SimPlan(nurse_delay_min=3 + 2 * i, nurse=nurse, offline=offline)

    def simulate(self, now: datetime, settings: Settings) -> None:
        """가짜 병상: 연결을 유지하고, critical 이 된 뒤 조금 있다가 간호사가 돌려 눕힌다."""
        to_turn: list[tuple[str, Posture, str]] = []
        with self._lock:
            for code, plan in self._sim.items():
                bed = self._beds.get(code)
                if bed is None or plan.offline:
                    continue
                bed.last_seen = now
                minutes = elapsed_minutes(bed.posture_since, now, settings.time_scale)
                # critical 1분(가속 시간) 뒤 담당 간호사가 알림 확인 (경고음이 계속 울리지 않게)
                if minutes >= settings.reposition_interval_min + 1:
                    for a in self._alerts:
                        if (
                            a.bed_code == code
                            and a.resolved_at is None
                            and a.acknowledged_at is None
                        ):
                            a.acknowledged_at, a.acknowledged_by = now, plan.nurse
                if minutes >= settings.reposition_interval_min + plan.nurse_delay_min:
                    plan.turn_index += 1
                    nxt = TURN_ORDER[plan.turn_index % len(TURN_ORDER)]
                    if nxt == bed.posture:
                        nxt = TURN_ORDER[(plan.turn_index + 1) % len(TURN_ORDER)]
                    to_turn.append((code, nxt, plan.nurse))
        for code, posture, nurse in to_turn:
            self.record_manual(code, posture, now, by=nurse)

    def tick(self, now: datetime, settings: Settings) -> list[Alert]:
        self.simulate(now, settings)
        return self.check_alerts(now, settings)

    # ----- 읽기 -----
    def list_beds(self) -> list[BedState]:
        with self._lock:
            return sorted((replace(b) for b in self._beds.values()), key=lambda b: b.bed_code)

    def get_bed(self, bed_code: str) -> BedState | None:
        with self._lock:
            bed = self._beds.get(bed_code)
            return replace(bed) if bed else None

    def history(self, bed_code: str) -> list[PostureEvent]:
        with self._lock:
            return [replace(e) for e in self._history.get(bed_code, [])]

    def alerts(self, limit: int = 50) -> list[Alert]:
        with self._lock:
            return [replace(a) for a in sorted(self._alerts, key=lambda a: -a.id)[:limit]]

    def clear(self) -> None:
        with self._lock:
            self._beds.clear()
            self._history.clear()
            self._alerts.clear()
            self._sim.clear()


store = MemoryBedStore()
