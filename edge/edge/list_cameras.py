"""연결된 카메라 번호 찾기.

iPhone 연속성 카메라, USB 웹캠, Mac 내장 카메라가 각각 몇 번인지 확인할 때 쓴다.
프레임은 열리는지 확인만 하고 저장하지 않는다. (D-002)

실행: edge/ 폴더에서
    python -m edge.list_cameras
"""

from collections.abc import Callable
from typing import Any

import cv2


def probe(max_index: int = 5, opener: Callable[[int], Any] = cv2.VideoCapture):
    """0 ~ max_index-1 번 카메라를 차례로 열어 보고 (번호, 가로, 세로) 목록을 돌려준다."""
    found: list[tuple[int, int, int]] = []
    for index in range(max_index):
        cap = opener(index)
        try:
            if not cap.isOpened():
                continue
            ok, frame = cap.read()
            if ok and frame is not None:
                h, w = frame.shape[:2]
                found.append((index, w, h))
        finally:
            cap.release()
    return found


def main() -> None:
    print("카메라를 찾는 중입니다... (몇 초 걸릴 수 있습니다)")
    found = probe()
    if not found:
        print("열 수 있는 카메라가 없습니다.")
        print("시스템 설정 → 개인정보 보호 및 보안 → 카메라에서 터미널/VS Code를 허용하세요.")
        raise SystemExit(1)
    for index, w, h in found:
        print(f"  --camera {index}   ({w}x{h})")
    print("어느 번호가 iPhone인지 모르겠으면 iPhone을 멀리 둔 뒤 다시 실행해")
    print("사라지는 번호를 찾으세요.")


if __name__ == "__main__":
    main()
