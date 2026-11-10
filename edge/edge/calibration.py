"""병상별 기준 자세(바로 누움) 등록 (T1-2 보정).

미리보기 창에서 환자(또는 시연자)가 바로 누운 상태로 `c` 키를 누르면
다음 몇 프레임의 측정값 중앙값을 기준으로 저장한다.
저장하는 것은 숫자 3개뿐이며 영상·좌표는 남기지 않는다 (D-002).
"""

from __future__ import annotations

import json
import logging
import re
import statistics
from dataclasses import asdict
from pathlib import Path

from edge.classify.posture import Calibration, Measures

logger = logging.getLogger(__name__)

# edge/edge/calibration.py → edge/calibration/
CALIBRATION_DIR = Path(__file__).resolve().parents[1] / "calibration"


def calibration_path(bed_id: str, base: Path = CALIBRATION_DIR) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", bed_id)
    return base / f"{safe}.json"


def load(bed_id: str, base: Path = CALIBRATION_DIR) -> Calibration | None:
    path = calibration_path(bed_id, base)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Calibration(
            float(data["z_diff"]),
            float(data["shoulder_ratio"]),
            None if data.get("hip_angle") is None else float(data["hip_angle"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("기준 자세 파일을 읽지 못했습니다 (%s): %s", path, exc)
        return None


def save(bed_id: str, cal: Calibration, base: Path = CALIBRATION_DIR) -> Path:
    path = calibration_path(bed_id, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cal), indent=2), encoding="utf-8")
    return path


class CalibrationCollector:
    """측정값을 n 개 모아 중앙값으로 Calibration 을 만든다."""

    def __init__(self, samples: int = 10) -> None:
        self.samples = samples
        self._items: list[Measures] = []

    def add(self, m: Measures) -> Calibration | None:
        self._items.append(m)
        if len(self._items) < self.samples:
            return None
        hips = [x.hip_angle for x in self._items if x.hip_angle is not None]
        return Calibration(
            round(statistics.median(x.z_diff for x in self._items), 4),
            round(statistics.median(x.shoulder_ratio for x in self._items), 4),
            round(statistics.median(hips), 1) if len(hips) >= self.samples // 2 else None,
        )

    @property
    def progress(self) -> str:
        return f"{len(self._items)}/{self.samples}"
