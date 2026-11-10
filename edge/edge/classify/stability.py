"""깜빡임 방지 필터 (T1-3).

프레임마다 나오는 자세 라벨은 흔들린다(관절이 잠깐 가려지거나 오인식).
같은 라벨이 `stable_sec`(POSTURE_STABLE_SEC, 기본 30초) 이상 이어질 때만 "자세 확정"으로 본다.

- 확정된 자세의 시작 시각은 그 라벨이 **처음 나타난 시각**이다.
  (posture_since 가 30초 늦게 찍히지 않게)
- `grace_sec` 보다 짧게 끼어든 다른 라벨(잠깐의 오인식)은 무시하고 기존 후보를 유지한다.
- `absent`(사람 없음), `unknown`(신뢰도 부족)도 같은 규칙으로 확정한다. (ARCHITECTURE 8장)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfirmedPosture:
    posture: str
    started_at: float  # 그 자세가 처음 관찰된 시각 (호출자가 넘긴 시계 기준, 보통 epoch 초)
    confidence: float  # 후보 기간 동안의 평균 신뢰도


@dataclass(slots=True)
class _Candidate:
    posture: str
    since: float
    conf_sum: float = 0.0
    count: int = 0

    def add(self, confidence: float) -> None:
        self.conf_sum += confidence
        self.count += 1

    @property
    def confidence(self) -> float:
        return self.conf_sum / self.count if self.count else 0.0


class StabilityFilter:
    def __init__(self, stable_sec: float = 30.0, grace_sec: float = 3.0) -> None:
        if stable_sec <= 0 or grace_sec < 0:
            raise ValueError("stable_sec 는 0보다 크고 grace_sec 는 0 이상이어야 합니다")
        self.stable_sec = stable_sec
        self.grace_sec = grace_sec
        self._confirmed: str | None = None
        self._candidate: _Candidate | None = None
        self._challenger: _Candidate | None = None

    @property
    def confirmed(self) -> str | None:
        """지금 확정된 자세. 아직 없으면 None."""
        return self._confirmed

    def update(self, posture: str, confidence: float, now: float) -> ConfirmedPosture | None:
        """프레임 1개의 판정을 넣는다. 자세가 새로 확정되면 ConfirmedPosture, 아니면 None."""
        cand = self._candidate
        if cand is None:
            cand = self._candidate = _Candidate(posture, now)
        elif posture == cand.posture:
            self._challenger = None  # 끼어들던 라벨은 잠깐의 오인식이었다
        else:
            ch = self._challenger
            if ch is None or ch.posture != posture:
                ch = self._challenger = _Candidate(posture, now)
            ch.add(confidence)
            if now - ch.since < self.grace_sec:
                return None  # 아직 오인식인지 실제 변화인지 모름 → 기존 후보 유지
            # grace_sec 넘게 이어졌으면 실제 변화로 보고 후보를 교체한다
            cand = self._candidate = ch
            self._challenger = None
            return self._maybe_confirm(cand, now)

        cand.add(confidence)
        return self._maybe_confirm(cand, now)

    def _maybe_confirm(self, cand: _Candidate, now: float) -> ConfirmedPosture | None:
        if cand.posture == self._confirmed or now - cand.since < self.stable_sec:
            return None
        self._confirmed = cand.posture
        return ConfirmedPosture(cand.posture, cand.since, round(cand.confidence, 3))
