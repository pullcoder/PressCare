"""포즈 추정 인터페이스·변환 테스트 (T1-1). 실제 모델·카메라 없이 돈다."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from edge.download_model import model_url
from edge.main import DetectionStats
from edge.pose import KP, Keypoint, PoseResult, create_estimator
from edge.pose.mediapipe_pose import (
    MediaPipePoseEstimator,
    PoseModelError,
    VideoTimestamp,
    default_model_path,
    landmarks_to_result,
    model_filename,
    to_rgb,
)


def make_pose(visibility: float = 0.9) -> PoseResult:
    return PoseResult(tuple(Keypoint(i / 100, 0.5, visibility) for i in range(33)))


def test_pose_result_needs_33_keypoints():
    with pytest.raises(ValueError):
        PoseResult((Keypoint(0, 0, 1),) * 10)


def test_pose_result_index_by_keypoint_name():
    pose = make_pose()
    assert pose[KP.LEFT_SHOULDER].x == pytest.approx(0.11)


def test_mean_visibility_uses_core_keypoints():
    kps = [Keypoint(0, 0, 0.0)] * 33
    for kp in (KP.NOSE, KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER, KP.LEFT_HIP, KP.RIGHT_HIP):
        kps[kp] = Keypoint(0, 0, 1.0)
    assert PoseResult(tuple(kps)).mean_visibility() == 1.0


def test_to_payload_matches_api_format():
    payload = make_pose(0.98765).to_payload()
    assert len(payload) == 33
    assert payload[1] == [0.01, 0.5, 0.988]


def test_landmarks_to_result_takes_first_person_and_handles_missing_visibility():
    person = [SimpleNamespace(x=0.1, y=0.2, visibility=None)] * 33
    other = [SimpleNamespace(x=0.9, y=0.9, visibility=1.0)] * 33
    pose = landmarks_to_result([person, other])
    assert pose is not None
    assert pose[0] == Keypoint(0.1, 0.2, 0.0)


def test_landmarks_to_result_none_when_no_person():
    assert landmarks_to_result([]) is None


def test_to_rgb_accepts_color_and_gray_ir_frames():
    bgr = np.zeros((4, 4, 3), np.uint8)
    bgr[..., 0] = 255  # 파랑
    assert to_rgb(bgr)[0, 0].tolist() == [0, 0, 255]
    gray = np.full((4, 4), 128, np.uint8)
    assert to_rgb(gray).shape == (4, 4, 3)


def test_video_timestamp_always_increases():
    ts = VideoTimestamp()
    assert [ts.next(t) for t in (0, 0, 5, 3, 100)] == [0, 1, 5, 6, 100]


def test_yolo_is_blocked_by_license_rule():
    with pytest.raises(ValueError, match="D-004"):
        create_estimator("yolo", Path("x"))


def test_unknown_backend_rejected():
    with pytest.raises(ValueError):
        create_estimator("openpose", Path("x"))


def test_missing_model_file_gives_download_hint(tmp_path):
    with pytest.raises(PoseModelError, match="download_model"):
        MediaPipePoseEstimator(tmp_path / "none.task")


def test_model_paths_and_urls():
    assert default_model_path("lite").name == "pose_landmarker_lite.task"
    assert default_model_path().parent.parts[-2:] == ("models", "weights")
    url = model_url("full")
    assert url.endswith("pose_landmarker_full/float16/latest/pose_landmarker_full.task")
    with pytest.raises(ValueError):
        model_filename("huge")


def test_detection_stats_summary():
    stats = DetectionStats()
    stats.add(make_pose(0.8))
    stats.add(None)
    assert stats.detection_rate == 0.5
    assert stats.mean_visibility == pytest.approx(0.8)
    assert "50%" in stats.summary()


def test_draw_overlay_runs_with_and_without_person():
    from edge.main import draw_overlay

    frame = np.zeros((240, 320, 3), np.uint8)
    draw_overlay(frame, "BED-01", 5.0, make_pose(0.1))  # 신뢰도 낮아도 그린다
    draw_overlay(frame, "BED-01", 5.0, None)
    assert frame.any()
