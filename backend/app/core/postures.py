"""자세·병상 상태 값 (CONVENTIONS 2장).

한글 표시는 frontend/src/shared/constants/posture.ts 와 맞춘다.
"""

from typing import Literal

Posture = Literal["supine", "left_lateral", "right_lateral", "sitting", "absent", "unknown"]
BedStatus = Literal["ok", "warning", "critical", "unknown", "offline"]
