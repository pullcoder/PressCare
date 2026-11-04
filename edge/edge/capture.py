"""카메라 프레임 읽기.

프레임은 메모리에서만 다루고 디스크에 저장하거나 밖으로 보내지 않는다. (D-002)
"""

import logging
import time
from collections.abc import Iterator

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def parse_source(source: str) -> int | str:
    """'0' 같은 숫자는 웹캠 번호, 그 외(rtsp://...)는 주소로 본다."""
    return int(source) if source.strip().isdigit() else source.strip()


class CameraError(RuntimeError):
    pass


class FrameSource:
    """카메라를 열고 지정한 FPS로 프레임을 꺼내 준다."""

    def __init__(self, source: str, fps: float) -> None:
        if fps <= 0:
            raise ValueError("fps는 0보다 커야 합니다.")
        self._source = parse_source(source)
        self._interval = 1.0 / fps
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise CameraError(
                "카메라를 열 수 없습니다. 다른 앱이 쓰는 중인지, 카메라 권한이 있는지, "
                "--camera 번호가 맞는지 확인하세요."
            )
        logger.info(
            "카메라 열림 (source=%s)", "webcam" if isinstance(self._source, int) else "rtsp"
        )

    def frames(self) -> Iterator[np.ndarray]:
        """FPS 간격으로 프레임을 하나씩 돌려준다. 읽기에 실패하면 멈춘다."""
        if self._cap is None:
            self.open()
        assert self._cap is not None
        next_at = time.monotonic()
        while True:
            ok, frame = self._cap.read()
            if not ok:
                logger.warning("프레임을 읽지 못해 종료합니다.")
                return
            now = time.monotonic()
            if now >= next_at:
                next_at = now + self._interval
                yield frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "FrameSource":
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
