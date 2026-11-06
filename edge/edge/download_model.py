"""MediaPipe 포즈 모델 내려받기 (처음 한 번).

실행: edge/ 폴더에서
    python -m edge.download_model            # lite (기본)
    python -m edge.download_model --variant full

받은 파일은 edge/models/weights/ 에 저장되며 git 에 올라가지 않는다.
"""

import argparse
import sys
import urllib.request
from pathlib import Path

from edge.pose.mediapipe_pose import MODEL_DIR, MODEL_VARIANTS, model_filename

BASE_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker"
MIN_BYTES = 1_000_000  # 이보다 작으면 오류 페이지를 받은 것으로 본다


def model_url(variant: str) -> str:
    return f"{BASE_URL}/pose_landmarker_{variant}/float16/latest/{model_filename(variant)}"


def download(variant: str, force: bool = False, model_dir: Path = MODEL_DIR) -> Path:
    target = model_dir / model_filename(variant)
    if target.is_file() and not force:
        print(f"이미 있습니다: {target}")
        return target

    model_dir.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(".part")
    url = model_url(variant)
    print(f"내려받는 중: {url}")
    with urllib.request.urlopen(url, timeout=60) as resp, part.open("wb") as out:
        while chunk := resp.read(1 << 16):
            out.write(chunk)
    if part.stat().st_size < MIN_BYTES:
        part.unlink()
        raise RuntimeError("받은 파일이 너무 작습니다. 네트워크 상태를 확인하세요.")
    part.replace(target)
    print(f"완료: {target} ({target.stat().st_size / 1e6:.1f} MB)")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="MediaPipe 포즈 모델 내려받기")
    parser.add_argument("--variant", choices=MODEL_VARIANTS, default="lite")
    parser.add_argument("--force", action="store_true", help="이미 있어도 다시 받기")
    args = parser.parse_args()
    try:
        download(args.variant, args.force)
    except Exception as exc:
        print(f"실패: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
