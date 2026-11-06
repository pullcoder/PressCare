"""엣지 에이전트 진입점.

카메라 프레임 → 포즈 추정(T1-1) → 자세 분류(T1-2) → 깜빡임 방지(T1-3) → backend 전송(T2-3).
--preview 창에 관절과 판정을 그린다. 영상은 저장·전송하지 않는다 (D-002).
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
from edge.classify.posture import PostureClassifier, Thresholds
from edge.classify.stability import StabilityFilter
from edge.client import BackendClient
from edge.config import get_settings
from edge.pipeline import FrameDecision, PosturePipeline
from edge.pose import KP, PoseResult, create_estimator
from edge.pose.mediapipe_pose import PoseModelError, default_model_path

logger = logging.getLogger("edge")

WINDOW_NAME = "PressCare preview (q: quit)"

# 미리보기에 그릴 뼈대 (얼굴·손가락은 생략)
SKELETON: tuple[tuple[KP, KP], ...] = (
    (KP.LEFT_EAR, KP.NOSE),
    (KP.NOSE, KP.RIGHT_EAR),
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
# 점으로 표시할 머리·몸통 관절과 화면에 신뢰도를 적을 관절
HEAD_AND_CORE: tuple[KP, ...] = (
    KP.NOSE,
    KP.LEFT_EAR,
    KP.RIGHT_EAR,
    KP.LEFT_SHOULDER,
    KP.RIGHT_SHOULDER,
    KP.LEFT_HIP,
    KP.RIGHT_HIP,
)
CORE_LABELS: tuple[tuple[str, KP], ...] = (
    ("nose", KP.NOSE),
    ("L shoulder", KP.LEFT_SHOULDER),
    ("R shoulder", KP.RIGHT_SHOULDER),
    ("L hip", KP.LEFT_HIP),
    ("R hip", KP.RIGHT_HIP),
)


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
    parser.add_argument(
        "--no-send", action="store_true", help="backend 로 보내지 않기 (인식만 확인)"
    )
    return parser


def vis_color(visibility: float) -> tuple[int, int, int]:
    """신뢰도별 색 (BGR): 0.6 이상 초록, 0.3 이상 노랑, 그 아래 빨강."""
    if visibility >= 0.6:
        return (0, 200, 0)
    if visibility >= MIN_DRAW_VISIBILITY:
        return (0, 220, 255)
    return (0, 0, 255)


def draw_overlay(
    frame,
    bed_id: str,
    fps: float,
    pose: PoseResult | None,
    decision: FrameDecision | None = None,
    confirmed: str | None = None,
) -> None:
    """미리보기 화면에만 그린다. 프레임은 저장하지 않는다. (cv2 글자는 영문만 가능)

    신뢰도가 낮은 관절도 빨간색으로 그려서 모델이 어디를 놓치는지 보이게 한다.
    """
    h, w = frame.shape[:2]

    def pt(kp: KP) -> tuple[int, int]:
        return int(pose[kp].x * w), int(pose[kp].y * h)

    lines = [f"{bed_id}  {fps:.1f} fps"]
    if pose is not None:
        for a, b in SKELETON:
            v = min(pose[a].visibility, pose[b].visibility)
            cv2.line(frame, pt(a), pt(b), vis_color(v), 3 if v >= MIN_DRAW_VISIBILITY else 1)
        for kp in HEAD_AND_CORE:
            cv2.circle(frame, pt(kp), 6, vis_color(pose[kp].visibility), -1)
        lines.append(f"person  core vis {pose.mean_visibility():.2f}")
        lines += [f"{name} {pose[kp].visibility:.2f}" for name, kp in CORE_LABELS]
    else:
        lines.append("no person")
    if decision is not None:
        lines.append(f"now: {decision.posture} ({decision.reason})")
        lines.append(f"confirmed: {confirmed or '-'}")
    for i, text in enumerate(lines):
        y = 30 + i * 26
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def run(camera: str, bed_id: str, fps: float, model: str, preview: bool, send: bool = True) -> int:
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

    client = (
        BackendClient(settings.edge_api_base_url, settings.edge_device_token, bed_id)
        if send
        else None
    )
    pipeline = PosturePipeline(
        PostureClassifier(Thresholds(min_confidence=settings.posture_min_confidence)),
        StabilityFilter(stable_sec=settings.posture_stable_sec),
        client,
        heartbeat_sec=settings.edge_heartbeat_sec,
    )

    logger.info(
        "시작: bed=%s fps=%.1f model=%s 확정=%.0f초 전송=%s",
        bed_id,
        fps,
        model,
        settings.posture_stable_sec,
        settings.edge_api_base_url if send else "끔",
    )
    stats = DetectionStats()
    started = time.monotonic()
    try:
        for frame in source.frames():
            elapsed = time.monotonic() - started
            pose = estimator.estimate(frame, int(elapsed * 1000))
            stats.add(pose)
            actual_fps = stats.frames / max(elapsed, 1e-6)
            decision = pipeline.process(pose, time.time(), actual_fps)
            if decision.confirmed is not None:
                logger.info("자세 확정: %s", decision.confirmed.posture)
            if preview:
                draw_overlay(
                    frame, bed_id, actual_fps, pose, decision, pipeline.stability.confirmed
                )
                cv2.imshow(WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
        estimator.close()
        if client is not None:
            client.close()
        if preview:
            cv2.destroyAllWindows()
    logger.info("종료: %s", stats.summary())
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()
    raise SystemExit(
        run(args.camera, args.bed_id, args.fps, args.model, args.preview, not args.no_send)
    )


if __name__ == "__main__":
    main()
