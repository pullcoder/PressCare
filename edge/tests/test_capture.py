import numpy as np
import pytest

from edge import capture
from edge.capture import CameraError, FrameSource, parse_source


def test_parse_source_webcam_number():
    assert parse_source("0") == 0
    assert parse_source(" 1 ") == 1


def test_parse_source_rtsp_address():
    assert parse_source("rtsp://camera.local/stream") == "rtsp://camera.local/stream"


def test_fps_must_be_positive():
    with pytest.raises(ValueError):
        FrameSource("0", 0)


class FakeCapture:
    """실제 카메라 없이 프레임 3장을 돌려주는 가짜 카메라."""

    def __init__(self, source, opened=True):
        self._opened = opened
        self._left = 3

    def isOpened(self):
        return self._opened

    def read(self):
        if self._left == 0:
            return False, None
        self._left -= 1
        return True, np.zeros((4, 4, 3), dtype=np.uint8)

    def release(self):
        pass


def test_frames_stop_when_camera_ends(monkeypatch):
    monkeypatch.setattr(capture.cv2, "VideoCapture", lambda src: FakeCapture(src))
    with FrameSource("0", fps=1000) as source:
        frames = list(source.frames())
    assert 1 <= len(frames) <= 3


def test_open_fails_with_clear_error(monkeypatch):
    monkeypatch.setattr(capture.cv2, "VideoCapture", lambda src: FakeCapture(src, opened=False))
    with pytest.raises(CameraError):
        FrameSource("0", fps=5).open()
