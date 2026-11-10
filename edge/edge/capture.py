"""카메라 프레임 읽기.

프레임은 메모리에서만 다루고 디스크에 저장하거나 밖으로 보내지 않는다. (D-002)
"""

import logging
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def parse_source(source: str) -> int | str:
    """'0' 같은 숫자는 카메라 번호, 영상 파일은 절대 경로, 그 외(rtsp://...)는 주소로 본다."""
    s = source.strip()
    if s.isdigit():
        return int(s)
    path = Path(s).expanduser()
    return str(path.resolve()) if path.is_file() else s


def is_video_file(source: int | str) -> bool:
    """시연·검증용 영상 파일인지 (카메라·스트림이 아닌지)."""
    return isinstance(source, str) and Path(source).is_file()


class CameraError(RuntimeError):
    pass


class FrameSource:
    """카메라를 열고 지정한 FPS로 프레임을 꺼내 준다."""

    def __init__(
        self,
        source: str,
        fps: float,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if fps <= 0:
            raise ValueError("fps는 0보다 커야 합니다.")
        self._source = parse_source(source)
        self._interval = 1.0 / fps
        self._cap: cv2.VideoCapture | None = None
        self._sleep = sleep
        self._clock = clock
        self.is_file = is_video_file(self._source)

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise CameraError(
                "카메라를 열 수 없습니다. 다른 앱이 쓰는 중인지, 카메라 권한이 있는지, "
                "--camera 번호가 맞는지 확인하세요."
            )
        kind = "camera" if isinstance(self._source, int) else "file" if self.is_file else "url"
        logger.info("카메라 열림 (source=%s)", kind)

    def frames(self) -> Iterator[np.ndarray]:
        """FPS 간격으로 프레임을 하나씩 돌려준다. 읽기에 실패하면 멈춘다."""
        if self._cap is None:
            self.open()
        assert self._cap is not None
        if self.is_file:
            yield from self._file_frames()
            return
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

    def _file_frames(self) -> Iterator[np.ndarray]:
        """영상 파일은 읽는 속도가 너무 빠르므로 원래 재생 속도에 맞춰 기다리며 꺼낸다."""
        assert self._cap is not None
        file_fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        if file_fps <= 0 or file_fps > 240:
            file_fps = 30.0
        start = self._clock()
        index = 0
        next_t = 0.0  # 다음에 넘겨줄 영상 속 시각 (초)
        while True:
            ok, frame = self._cap.read()
            if not ok:
                logger.info("영상이 끝났습니다.")
                return
            t = index / file_fps
            index += 1
            if t + 1e-9 < next_t:
                continue  # 처리 FPS 보다 촘촘한 프레임은 건너뛴다
            next_t = t + self._interval
            wait = start + t - self._clock()
            if wait > 0:
                self._sleep(wait)
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
