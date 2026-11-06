import numpy as np

from edge.list_cameras import probe


class FakeCap:
    def __init__(self, index: int) -> None:
        self.index = index
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802 - OpenCV 이름 그대로
        return self.index in (0, 2)

    def read(self):
        if self.index == 2:
            return True, np.zeros((1080, 1920, 3), np.uint8)
        return False, None  # 열리지만 프레임이 안 나오는 장치

    def release(self) -> None:
        self.released = True


def test_probe_lists_only_cameras_that_give_frames():
    caps: list[FakeCap] = []

    def opener(i: int) -> FakeCap:
        caps.append(FakeCap(i))
        return caps[-1]

    assert probe(4, opener) == [(2, 1920, 1080)]
    assert all(c.released for c in caps)
