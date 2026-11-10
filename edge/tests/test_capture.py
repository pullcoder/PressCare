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


class FakeVideoFile:
    """30fps 영상 3초(90프레임)짜리 가짜 파일."""

    def __init__(self, source):
        self._left = 90

    def isOpened(self):
        return True

    def get(self, prop):
        return 30.0

    def read(self):
        if self._left == 0:
            return False, None
        self._left -= 1
        return True, np.zeros((4, 4, 3), dtype=np.uint8)

    def release(self):
        pass


def test_video_file_plays_at_real_speed(monkeypatch, tmp_path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"x")
    monkeypatch.setattr(capture.cv2, "VideoCapture", FakeVideoFile)

    now = [0.0]
    slept: list[float] = []

    def fake_sleep(sec: float) -> None:
        slept.append(sec)
        now[0] += sec

    src = FrameSource(str(video), fps=5, sleep=fake_sleep, clock=lambda: now[0])
    assert src.is_file
    frames = list(src.frames())
    assert len(frames) == 15  # 3초 × 5fps
    assert now[0] == pytest.approx(2.8)  # 마지막 프레임(2.8초)까지 실제 시간만큼 기다림


def test_parse_source_file_path(tmp_path):
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")
    assert parse_source(str(video)) == str(video.resolve())
    assert parse_source(str(tmp_path / "none.mp4")) == str(tmp_path / "none.mp4")
