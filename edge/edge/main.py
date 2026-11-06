"""엣지 에이전트 진입점.

지금은 카메라 프레임 → 포즈 추정(T1-1)까지 하고, --preview 창에 관절을 그린다.
자세 분류(T1-2)·깜빡임 방지(T1-3)·서버 전송(T2-3)은 이후 단계에서 붙인다.
종료할 때 사람 검출률과 주요 관절 신뢰도를 출력한다 (인식 검증 T1-0 참고용).

실행: edge/ 폴더에서
    python -m edge.download_model                       # 처음 한 번
    python -m edge.main --camera 0 --bed-id BED-01 --preview
"""

import argparse
import logging
import time
from dataclasses import dataclass, field

import cv2

from edge.capture import CameraError, FrameSource
from edge.config import get_settings
from edge.pose import KP, PoseResult, create_estimator
from edge.pose.mediapipe_pose import PoseModelError, default_model_path

logger = logging.getLogger("edge")

WINDOW_NAME = "PressCare preview (q: quit)"

# 미리보기에 그릴 뼈대 (얼굴·손가락은 생략)
SKELETON: tuple[tuple[KP, KP], ...] = (
    (KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER),
    (KP.LEFT_SHOULDER, KP.LEFT_ELBOW),
    (KP.LEFT_ELBOW, KP.LEFT_WRIST),
    (KP.RIGHT_SHOULDER, KP.RIGHT_ELBOW),
    (KP.RIGHT_ELBOW, KP.RIGHT_WRIST),
    (KP.LEFT_SHOULDER, KP.LEFT_HIP),
    (KP.RIGHT_SHOULDER, KP.RIGHT_HIP),
    (KP.LEFT_HIP, KP.RIGHT_HIP),
    (KP.LEFT_HIP, KP.LEFT_KNEE),
    (KP.LEFT_KNEE, KP.LEFT_ANKLE),
    (KP.RIGHT_HIP, KP.RIGHT_KNEE),
    (KP.RIGHT_KNEE, KP.RIGHT_ANKLE),
)
MIN_DRAW_VISIBILITY = 0.3


@dataclass
class DetectionStats:
    """프레임별 검출 결과를 모아 종료 시 요약한다. 좌표·영상은 남기지 않는다."""

    frames: int = 0
    detected: int = 0
    visibilities: list[float] = field(default_factory=list)

    def add(self, pose: PoseResult | None) -> None:
        self.frames += 1
        if pose is not None:
            self.detected += 1
            self.visibilities.append(pose.mean_visibility())

    @property
    def detection_rate(self) -> float:
        return self.detected / self.frames if self.frames else 0.0

    @property
    def mean_visibility(self) -> float:
        v = self.visibilities
        return sum(v) / len(v) if v else 0.0

    def summary(self) -> str:
        return (
            f"사람 검출률 {self.detection_rate:.0%} ({self.detected}/{self.frames}), "
            f"주요 관절 평균 신뢰도 {self.mean_visibility:.2f}"
        )


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="PressCare 엣지 에이전트")
    parser.add_argument("--camera", default=settings.camera_source, help="웹캠 번호 또는 RTSP 주소")
    parser.add_argument("--bed-id", required=True, help="병상 코드 (예: BED-01)")
    parser.add_argument("--fps", type=float, default=settings.camera_fps, help="초당 처리 프레임")
    parser.add_argument(
        "--model", default=settings.pose_model, choices=("lite", "full", "heavy"), help="포즈 모델"
    )
    parser.add_argument("--preview", action="store_true", help="개발용 미리보기 창 표시")
    return parser


def draw_overlay(frame, bed_id: str, fps: float, pose: PoseResult | None) -> None:
    """미리보기 화면에만 그린다. 프레임은 저장하지 않는다. (cv2 글자는 영문만 가능)"""
    h, w = frame.shape[:2]
    if pose is not None:
        for a, b in SKELETON:
            ka, kb = pose[a], pose[b]
            if min(ka.visibility, kb.visibility) < MIN_DRAW_VISIBILITY:
                continue
            pa = (int(ka.x * w), int(ka.y * h))
            pb = (int(kb.x * w), int(kb.y * h))
            cv2.line(frame, pa, pb, (0, 200, 255), 2)
        status = f"person  vis {pose.mean_visibility():.2f}"
    else:
        status = "no person"
    cv2.putText(
        frame, f"{bed_id}  {fps:.1f} fps", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
    )
    cv2.putText(frame, status, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)


def run(camera: str, bed_id: str, fps: float, model: str, preview: bool) -> int:
    settings = get_settings()
    if settings.save_raw_frames:
        # 저장 기능은 존재하지 않는다. 설정이 켜져 있어도 무시하고 알린다. (D-002)
        logger.warning("SAVE_RAW_FRAMES=true 는 무시됩니다. 원본 프레임은 저장하지 않습니다.")

    try:
        estimator = create_estimator(settings.pose_backend, default_model_path(model))
    except (PoseModelError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    try:
        source = FrameSource(camera, fps)
        source.open()
    except CameraError as exc:
        logger.error("%s", exc)
        estimator.close()
        return 1

    logger.info("시작: bed=%s fps=%.1f model=%s preview=%s", bed_id, fps, model, preview)
    stats = DetectionStats()
    started = time.monotonic()
    try:
        for frame in source.frames():
            elapsed = time.monotonic() - started
            pose = estimator.estimate(frame, int(elapsed * 1000))
            stats.add(pose)
            # TODO(T1-2, T1-3): posture_classifier → stability_filter → client(T2-3)
            if preview:
                draw_overlay(frame, bed_id, stats.frames / max(elapsed, 1e-6), pose)
                cv2.imshow(WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
        estimator.close()
        if preview:
            cv2.destroyAllWindows()
    logger.info("종료: %s", stats.summary())
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()
    raise SystemExit(run(args.camera, args.bed_id, args.fps, args.model, args.preview))


if __name__ == "__main__":
    main()
