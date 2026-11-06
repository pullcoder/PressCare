"""MediaPipe Pose Landmarker 구현 (T1-1, D-004 — Apache 2.0).

모델 파일(.task)은 저장소에 커밋하지 않는다(.gitignore `models/weights/`).
처음 한 번 `python -m edge.download_model` 로 받는다.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from edge.pose.base import Keypoint, PoseEstimator, PoseResult

# edge/edge/pose/mediapipe_pose.py → edge/models/weights
MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "weights"
MODEL_VARIANTS = ("lite", "full", "heavy")  # 오른쪽으로 갈수록 정확도↑ 속도↓


class PoseModelError(RuntimeError):
    """모델 파일이 없거나 불러올 수 없을 때."""


def model_filename(variant: str) -> str:
    if variant not in MODEL_VARIANTS:
        raise ValueError(f"모델 종류는 {MODEL_VARIANTS} 중 하나여야 합니다: {variant!r}")
    return f"pose_landmarker_{variant}.task"


def default_model_path(variant: str = "lite") -> Path:
    return MODEL_DIR / model_filename(variant)


def to_rgb(frame: np.ndarray) -> np.ndarray:
    """OpenCV BGR 또는 흑백(IR 야간) 프레임 → MediaPipe 입력용 RGB."""
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def landmarks_to_result(poses: Sequence[Sequence[Any]]) -> PoseResult | None:
    """MediaPipe 결과(사람별 관절 목록) → PoseResult. 사람이 없으면 None."""
    if not poses:
        return None
    return PoseResult(
        tuple(
            Keypoint(float(lm.x), float(lm.y), float(lm.visibility or 0.0), float(lm.z or 0.0))
            for lm in poses[0]
        )
    )


class VideoTimestamp:
    """VIDEO 모드는 시각(ms)이 반드시 계속 커져야 하므로 같거나 작은 값은 1ms 올린다."""

    def __init__(self) -> None:
        self._last = -1

    def next(self, timestamp_ms: int) -> int:
        ts = max(int(timestamp_ms), self._last + 1)
        self._last = ts
        return ts


class MediaPipePoseEstimator(PoseEstimator):
    def __init__(
        self,
        model_path: Path,
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        if not model_path.is_file():
            raise PoseModelError(
                f"모델 파일이 없습니다: {model_path}\n"
                "edge/ 폴더에서 먼저 실행하세요: python -m edge.download_model"
            )

        # mediapipe 는 무거워서 실제로 쓸 때만 불러온다 (테스트는 mediapipe 없이도 돈다).
        import mediapipe as mp
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import pose_landmarker
        from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
            VisionTaskRunningMode,
        )

        options = pose_landmarker.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=VisionTaskRunningMode.VIDEO,
            num_poses=1,  # 병상당 카메라 1대, 환자 1명
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        try:
            self._landmarker = pose_landmarker.PoseLandmarker.create_from_options(options)
        except Exception as exc:  # 손상된 파일 등
            raise PoseModelError(f"모델을 불러오지 못했습니다: {model_path} ({exc})") from exc
        self._mp = mp
        self._timestamp = VideoTimestamp()

    def estimate(self, frame: np.ndarray, timestamp_ms: int) -> PoseResult | None:
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=to_rgb(frame))
        result = self._landmarker.detect_for_video(image, self._timestamp.next(timestamp_ms))
        return landmarks_to_result(result.pose_landmarks)

    def close(self) -> None:
        self._landmarker.close()
