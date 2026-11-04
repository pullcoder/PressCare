"""엣지 에이전트 진입점 (T0-5 뼈대).

지금은 카메라 프레임을 읽어 --preview 창에 보여주기만 한다.
포즈 추정·자세 분류(T1), 서버 전송(T2-3)은 이후 단계에서 붙인다.

실행: edge/ 폴더에서
    python -m edge.main --camera 0 --bed-id BED-01 --preview
"""

import argparse
import logging
import time

import cv2

from edge.capture import CameraError, FrameSource
from edge.config import get_settings

logger = logging.getLogger("edge")

WINDOW_NAME = "PressCare preview (q: 종료)"


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="PressCare 엣지 에이전트")
    parser.add_argument("--camera", default=settings.camera_source, help="웹캠 번호 또는 RTSP 주소")
    parser.add_argument("--bed-id", required=True, help="병상 코드 (예: BED-01)")
    parser.add_argument("--fps", type=float, default=settings.camera_fps, help="초당 처리 프레임")
    parser.add_argument("--preview", action="store_true", help="개발용 미리보기 창 표시")
    return parser


def draw_overlay(frame, bed_id: str, fps: float) -> None:
    """미리보기 화면에만 표시한다. 프레임은 저장하지 않는다."""
    cv2.putText(
        frame,
        f"{bed_id}  {fps:.1f} fps",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
    )


def run(camera: str, bed_id: str, fps: float, preview: bool) -> int:
    if get_settings().save_raw_frames:
        # 저장 기능은 존재하지 않는다. 설정이 켜져 있어도 무시하고 알린다. (D-002)
        logger.warning("SAVE_RAW_FRAMES=true 는 무시됩니다. 원본 프레임은 저장하지 않습니다.")

    try:
        source = FrameSource(camera, fps)
        source.open()
    except CameraError as exc:
        logger.error("%s", exc)
        return 1

    logger.info("시작: bed=%s fps=%.1f preview=%s", bed_id, fps, preview)
    count, started = 0, time.monotonic()
    try:
        for frame in source.frames():
            count += 1
            actual_fps = count / max(time.monotonic() - started, 1e-6)
            # TODO(T1): pose_estimator → posture_classifier → stability_filter
            if preview:
                draw_overlay(frame, bed_id, actual_fps)
                cv2.imshow(WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
        if preview:
            cv2.destroyAllWindows()
    logger.info("종료: 처리 프레임 %d개", count)
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()
    raise SystemExit(run(args.camera, args.bed_id, args.fps, args.preview))


if __name__ == "__main__":
    main()
