#!/bin/bash
# PressCare 시연용: 백엔드 + 프론트 + 엣지를 한 번에 켠다 (Mac).
#
# 사용법 (Mac 터미널 앱에서. VS Code 터미널은 카메라 권한이 막힐 수 있음)
#   cd ~/Documents/PressCare
#   ./scripts/demo.sh          # iPhone 카메라 1번, 병상 BED-01
#   ./scripts/demo.sh 0        # 카메라 번호 바꾸기
#   ./scripts/demo.sh 1 BED-02 # 병상 코드 바꾸기
#   ./scripts/demo.sh ~/Desktop/demo.mp4   # 카메라 대신 영상 파일 (실제 속도로 재생)
# 끄기: 미리보기 창에서 q, 또는 터미널에서 Ctrl+C → 셋 다 같이 꺼진다.
# 로그: .demo-backend.log, .demo-frontend.log (git 에 올라가지 않음)

set -euo pipefail

CAMERA="${1:-1}"
BED="${2:-BED-01}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# conda 환경 켜기
if ! command -v conda >/dev/null 2>&1 && [ -x /opt/miniconda3/bin/conda ]; then
  export PATH="/opt/miniconda3/bin:$PATH"
fi
eval "$(conda shell.bash hook)"
conda activate presscare

# 이미 켜져 있는 서버가 있으면 멈춘다 (포트 충돌 방지)
for port in 8000 5173; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "⚠ $port 번 포트가 이미 사용 중입니다. 켜 둔 백엔드/프론트를 먼저 꺼 주세요 (Ctrl+C)."
    exit 1
  fi
done

if [ ! -f "$ROOT/.env" ]; then
  echo "⚠ .env 파일이 없습니다. cp .env.example .env 로 만든 뒤 다시 실행하세요."
  exit 1
fi

# 스크립트가 끝나면 함께 켠 프로그램도 모두 끈다
trap 'trap - EXIT INT TERM; kill 0 2>/dev/null' EXIT INT TERM

echo "▶ 백엔드 켜는 중 (http://localhost:8000/docs)"
(cd "$ROOT/backend" && uvicorn app.main:app --port 8000 >"$ROOT/.demo-backend.log" 2>&1) &

echo "▶ 프론트 켜는 중 (http://localhost:5173)"
(cd "$ROOT/frontend" && npm run dev -- --port 5173 --strictPort >"$ROOT/.demo-frontend.log" 2>&1) &

sleep 4
open "http://localhost:5173" || true

echo "▶ 엣지 실행 (카메라 $CAMERA, 병상 $BED). 미리보기 창에서 c: 기준 자세 등록, q: 종료"
cd "$ROOT/edge"
python -m edge.main --camera "$CAMERA" --bed-id "$BED" --preview
