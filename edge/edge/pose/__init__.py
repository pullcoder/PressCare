"""포즈 추정 (T1-1). `create_estimator()` 로 설정값에 맞는 추정기를 만든다."""

from pathlib import Path

from edge.pose.base import CORE_KEYPOINTS, KP, Keypoint, PoseEstimator, PoseResult


def create_estimator(backend: str, model_path: Path) -> PoseEstimator:
    if backend == "mediapipe":
        from edge.pose.mediapipe_pose import MediaPipePoseEstimator

        return MediaPipePoseEstimator(model_path)
    if backend == "yolo":
        raise ValueError("YOLO 는 라이선스(AGPL-3.0) 확인 전 사용 금지입니다. (D-004)")
    raise ValueError(f"알 수 없는 POSE_BACKEND: {backend!r} (mediapipe 만 지원)")


__all__ = ["CORE_KEYPOINTS", "KP", "Keypoint", "PoseEstimator", "PoseResult", "create_estimator"]
