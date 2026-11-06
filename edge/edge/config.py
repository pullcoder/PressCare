"""엣지 설정.

저장소 루트의 `.env` 하나에서 읽는다 (`.env.example`을 복사해 만든다).
기준값은 코드에 하드코딩하지 않는다. (AGENTS.md 4-6)
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# edge/edge/config.py → 저장소 루트
REPO_ROOT = Path(__file__).resolve().parents[2]


class EdgeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    camera_source: str = "0"  # 웹캠 번호 또는 RTSP 주소
    camera_fps: float = 5.0  # 자세 판별엔 초당 5프레임이면 충분
    save_raw_frames: bool = False  # 항상 False. 저장 기능은 만들지 않는다 (D-002)
    pose_backend: Literal["mediapipe", "yolo"] = "mediapipe"  # yolo 는 사용 금지 (D-004)
    pose_model: Literal["lite", "full", "heavy"] = "lite"  # 정확도↑ 속도↓ 순
    posture_stable_sec: float = 30.0  # 같은 자세가 이만큼 이어져야 확정 (T1-3)
    posture_min_confidence: float = 0.6  # 이보다 낮으면 unknown (T1-2)


@lru_cache
def get_settings() -> EdgeSettings:
    return EdgeSettings()
