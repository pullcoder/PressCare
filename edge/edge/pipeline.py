"""프레임 1장의 처리 흐름: 관절 → 자세 라벨 → 깜빡임 방지 → backend 전송.

카메라·모델과 분리해 두어 테스트에서 가짜 관절 좌표로 전체 흐름을 확인할 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass

from edge.classify.posture import PostureClassifier
from edge.classify.stability import ConfirmedPosture, StabilityFilter
from edge.client import BackendClient
from edge.pose.base import PoseResult


@dataclass(frozen=True, slots=True)
class FrameDecision:
    posture: str  # 이 프레임의 판정 (확정 전)
    confidence: float
    reason: str
    confirmed: ConfirmedPosture | None  # 이 프레임에서 새로 확정됐으면 값이 있다


class PosturePipeline:
    def __init__(
        self,
        classifier: PostureClassifier,
        stability: StabilityFilter,
        client: BackendClient | None = None,
        heartbeat_sec: float = 60.0,
    ) -> None:
        self.classifier = classifier
        self.stability = stability
        self.client = client
        self.heartbeat_sec = heartbeat_sec
        self._next_heartbeat = 0.0  # 시작하자마자 한 번 보내 병상이 화면에 나타나게 한다
        self._last_conf = 0.0

    def process(self, pose: PoseResult | None, now: float, fps: float) -> FrameDecision:
        if pose is None:
            posture, conf, reason = "absent", 0.0, "no person"
        else:
            r = self.classifier.classify(pose)
            posture, conf, reason = r.posture, r.confidence, r.reason

        confirmed = self.stability.update(posture, conf, now)
        if confirmed is not None:
            self._last_conf = confirmed.confidence
            if self.client is not None:
                keypoints = pose.to_payload() if pose is not None else None
                self.client.send_posture_event(confirmed, keypoints, now)
        elif self.client is not None:
            self.client.retry(now)

        if self.client is not None and now >= self._next_heartbeat:
            self._next_heartbeat = now + self.heartbeat_sec
            current = self.stability.confirmed or "unknown"
            self.client.send_heartbeat(current, self._last_conf, fps)

        return FrameDecision(posture, conf, reason, confirmed)
