"""규칙 기반 자세 분류 (T1-2, D-006).

관절 좌표 → supine / left_lateral / right_lateral / sitting / unknown.
(absent 는 사람이 검출되지 않을 때 main 에서 정한다.)

판단 순서
1. 주요 관절(코·어깨·엉덩이) 평균 신뢰도 < POSTURE_MIN_CONFIDENCE → unknown
2. 측위: 양 어깨·엉덩이의 카메라 거리(z) 차이가 크거나, 어깨 폭이 몸통 길이에 비해 좁으면 측위.
   위쪽(카메라에 가까운) 어깨가 오른쪽이면 왼쪽이 바닥 → left_lateral. 30° 측위도 측위로 본다.
3. 앉음: 어깨–엉덩이–무릎 각도가 접혀 있으면 sitting (무릎이 보일 때만)
4. 나머지 → supine

⚠ 기준값은 임시값이다. 1주차 인식 검증(T1-0) 결과로 조정한다 (D-013).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from edge.pose.base import KP, Keypoint, PoseResult


@dataclass(frozen=True, slots=True)
class Thresholds:
    min_confidence: float = 0.6  # POSTURE_MIN_CONFIDENCE
    lateral_z_diff: float = 0.12  # 좌우 어깨·엉덩이 z 차이 평균이 이 이상이면 측위
    narrow_shoulder_ratio: float = 0.35  # 어깨 폭 / 몸통 길이가 이 미만이면 측위
    sitting_hip_angle: float = 125.0  # 어깨–엉덩이–무릎 각도(도)가 이 미만이면 앉음
    min_knee_visibility: float = 0.5


@dataclass(frozen=True, slots=True)
class PostureResult:
    posture: str
    confidence: float
    reason: str  # 미리보기·디버깅용 짧은 설명 (영문, cv2 표시용)


def _mid(a: Keypoint, b: Keypoint) -> tuple[float, float]:
    return (a.x + b.x) / 2, (a.y + b.y) / 2


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angle(a: Keypoint, b: Keypoint, c: Keypoint) -> float:
    """b 에서 a 와 c 가 이루는 각도 (도)."""
    v1 = (a.x - b.x, a.y - b.y)
    v2 = (c.x - b.x, c.y - b.y)
    n = math.hypot(*v1) * math.hypot(*v2)
    if n == 0:
        return 180.0
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / n))
    return math.degrees(math.acos(cos))


class PostureClassifier:
    def __init__(self, thresholds: Thresholds | None = None) -> None:
        self.t = thresholds or Thresholds()

    def classify(self, pose: PoseResult) -> PostureResult:
        t = self.t
        conf = round(pose.mean_visibility(), 3)
        if conf < t.min_confidence:
            return PostureResult("unknown", conf, f"low vis {conf:.2f}")

        ls, rs = pose[KP.LEFT_SHOULDER], pose[KP.RIGHT_SHOULDER]
        lh, rh = pose[KP.LEFT_HIP], pose[KP.RIGHT_HIP]

        # z 가 클수록 카메라에서 멀다. 왼쪽이 멀면(아래) 왼쪽으로 누운 것.
        z_diff = ((ls.z - rs.z) + (lh.z - rh.z)) / 2
        torso = _dist(_mid(ls, rs), _mid(lh, rh))
        ratio = math.hypot(ls.x - rs.x, ls.y - rs.y) / torso if torso > 0 else 0.0

        if abs(z_diff) >= t.lateral_z_diff or ratio < t.narrow_shoulder_ratio:
            side = "left_lateral" if z_diff >= 0 else "right_lateral"
            return PostureResult(side, conf, f"lateral dz {z_diff:+.2f} w {ratio:.2f}")

        lk, rk = pose[KP.LEFT_KNEE], pose[KP.RIGHT_KNEE]
        if min(lk.visibility, rk.visibility) >= t.min_knee_visibility:
            hip_angle = (_angle(ls, lh, lk) + _angle(rs, rh, rk)) / 2
            if hip_angle < t.sitting_hip_angle:
                return PostureResult("sitting", conf, f"hip {hip_angle:.0f}deg")

        return PostureResult("supine", conf, f"dz {z_diff:+.2f} w {ratio:.2f}")
