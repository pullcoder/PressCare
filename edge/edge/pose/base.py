"""포즈 추정기 인터페이스 (T1-1).

추정기를 바꿔도(MediaPipe → RTMPose 등) 자세 분류기와 필터 코드는 그대로 쓰도록
반환 형식을 여기서 하나로 정한다. (D-004)
관절 번호는 MediaPipe Pose 33개 기준이며, 다른 추정기도 이 번호로 맞춰 반환한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum
from types import TracebackType

import numpy as np

NUM_KEYPOINTS = 33


class KP(IntEnum):
    """관절 번호 (MediaPipe Pose 기준). 왼쪽/오른쪽은 환자 본인 기준이다."""

    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


# 자세 판단에 꼭 필요한 관절. 인식 검증(T1-0) 때 이 관절들의 신뢰도를 본다.
CORE_KEYPOINTS: tuple[KP, ...] = (
    KP.NOSE,
    KP.LEFT_SHOULDER,
    KP.RIGHT_SHOULDER,
    KP.LEFT_HIP,
    KP.RIGHT_HIP,
)


@dataclass(frozen=True, slots=True)
class Keypoint:
    x: float  # 화면 왼쪽 0 → 오른쪽 1 (화면 밖이면 범위를 벗어날 수 있음)
    y: float  # 화면 위 0 → 아래 1
    visibility: float  # 0~1, 관절이 보이는 정도


@dataclass(frozen=True, slots=True)
class PoseResult:
    """사람 1명의 관절 좌표 33개."""

    keypoints: tuple[Keypoint, ...]

    def __post_init__(self) -> None:
        if len(self.keypoints) != NUM_KEYPOINTS:
            raise ValueError(f"관절은 {NUM_KEYPOINTS}개여야 합니다: {len(self.keypoints)}개")

    def __getitem__(self, kp: KP | int) -> Keypoint:
        return self.keypoints[int(kp)]

    def mean_visibility(self, kps: Iterable[KP] = CORE_KEYPOINTS) -> float:
        values = [self[kp].visibility for kp in kps]
        return sum(values) / len(values) if values else 0.0

    def to_payload(self, ndigits: int = 3) -> list[list[float]]:
        """API.md `keypoints` 형식: [[x, y, visibility], ...] 33개."""
        return [
            [round(k.x, ndigits), round(k.y, ndigits), round(k.visibility, ndigits)]
            for k in self.keypoints
        ]


class PoseEstimator(ABC):
    """프레임 1장 → 관절 좌표. 프레임은 메모리에서만 쓰고 저장하지 않는다. (D-002)"""

    @abstractmethod
    def estimate(self, frame: np.ndarray, timestamp_ms: int) -> PoseResult | None:
        """BGR(또는 흑백 IR) 프레임에서 사람 1명의 관절을 찾는다. 없으면 None."""

    def close(self) -> None:  # noqa: B027 - 정리할 것이 없는 구현도 있다
        """모델 자원을 정리한다."""

    def __enter__(self) -> PoseEstimator:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
