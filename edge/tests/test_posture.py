"""규칙 기반 자세 분류 테스트 (T1-2). 손으로 만든 좌표로 각 규칙을 확인한다."""

import pytest

from edge.classify.posture import PostureClassifier, Thresholds
from edge.pose.base import KP, Keypoint, PoseResult


def body(
    *,
    shoulder_w: float = 0.2,
    z_left: float = 0.0,
    knee: tuple[float, float] = (0.0, 0.25),
    vis: float = 0.9,
    knee_vis: float = 0.9,
) -> PoseResult:
    """위에서 내려다본 사람 (머리가 위, 다리가 아래). knee 는 엉덩이 기준 (dx, dy)."""
    kps = [Keypoint(0.5, 0.5, 0.0)] * 33
    half = shoulder_w / 2

    def put(kp: KP, x: float, y: float, v: float = vis, z: float = 0.0) -> None:
        kps[kp] = Keypoint(x, y, v, z)

    put(KP.NOSE, 0.5, 0.15)
    put(KP.LEFT_SHOULDER, 0.5 + half, 0.3, z=z_left)
    put(KP.RIGHT_SHOULDER, 0.5 - half, 0.3, z=-z_left)
    put(KP.LEFT_HIP, 0.5 + half * 0.8, 0.6, z=z_left)
    put(KP.RIGHT_HIP, 0.5 - half * 0.8, 0.6, z=-z_left)
    put(KP.LEFT_KNEE, 0.5 + half * 0.8 + knee[0], 0.6 + knee[1], v=knee_vis)
    put(KP.RIGHT_KNEE, 0.5 - half * 0.8 + knee[0], 0.6 + knee[1], v=knee_vis)
    return PoseResult(tuple(kps))


clf = PostureClassifier()


def test_supine_wide_shoulders_flat():
    assert clf.classify(body()).posture == "supine"


def test_low_visibility_is_unknown():
    r = clf.classify(body(vis=0.3))
    assert r.posture == "unknown"
    assert r.confidence == pytest.approx(0.3)


@pytest.mark.parametrize(
    ("z_left", "expected"),
    [(0.1, "left_lateral"), (-0.1, "right_lateral")],
)
def test_thirty_degree_lateral_by_depth(z_left, expected):
    # 어깨 폭은 넓게 보여도(30° 측위) 좌우 깊이 차이로 측위를 잡는다
    assert clf.classify(body(z_left=z_left)).posture == expected


def test_lateral_by_narrow_shoulders():
    r = clf.classify(body(shoulder_w=0.05, z_left=0.02))
    assert r.posture == "left_lateral"


def test_sitting_when_hips_folded():
    # 무릎이 몸통 쪽(옆)으로 접혀 어깨–엉덩이–무릎이 약 90°
    assert clf.classify(body(knee=(0.25, 0.0))).posture == "sitting"


def test_hidden_knees_skip_sitting_rule():
    r = clf.classify(body(knee=(0.25, 0.0), knee_vis=0.1))
    assert r.posture == "supine"


def test_thresholds_are_adjustable():
    strict = PostureClassifier(Thresholds(lateral_z_diff=0.5))
    assert strict.classify(body(z_left=0.1)).posture == "supine"


def angled_supine() -> PoseResult:
    """옆 사선 카메라로 본 '바로 누운' 사람: 한쪽이 가깝고 어깨가 좁아 보인다."""
    return body(shoulder_w=0.06, z_left=0.08)


def test_angled_camera_misreads_without_calibration():
    assert clf.classify(angled_supine()).posture != "supine"


def test_calibration_makes_angled_supine_supine():
    from edge.classify.posture import Calibration, measure

    m = measure(angled_supine())
    cal = Calibration(m.z_diff, m.shoulder_ratio, m.hip_angle)
    calibrated = PostureClassifier(calibration=cal)
    assert calibrated.classify(angled_supine()).posture == "supine"
    # 기준보다 한쪽이 더 멀어지면(돌아누우면) 측위
    assert calibrated.classify(body(shoulder_w=0.06, z_left=0.2)).posture == "left_lateral"
    assert calibrated.classify(body(shoulder_w=0.06, z_left=-0.06)).posture == "right_lateral"
