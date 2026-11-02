# SETUP — 개발 환경 설치

> Windows 기준으로 쓰고, macOS/Linux 차이는 괄호로 적었습니다.

## 1. 설치할 프로그램

| 프로그램 | 버전 | 확인 명령 |
|---------|------|----------|
| Git | 최신 | `git --version` |
| Python | **3.11.x** | `python --version` |
| Node.js | 20 LTS 이상 | `node -v`, `npm -v` |
| Docker Desktop | 최신 | `docker --version` |
| VS Code | 최신 | 추천 확장: Python, Ruff, ESLint, Prettier, Tailwind CSS IntelliSense |
| 웹캠 | USB 웹캠 1대 (720p 이상) | 카메라 앱으로 화면 나오는지 확인 |

> Python 3.12 이상은 MediaPipe 호환을 확인한 뒤 올린다 (D-005).

## 2. 저장소 받기

```bash
git clone https://github.com/pullcoder/PressCare.git
cd PressCare
cp .env.example .env            # Windows: copy .env.example .env
```

`.env`에서 최소한 `POSTGRES_PASSWORD`, `JWT_SECRET`을 채운다. `DATABASE_URL`의 `<password>`도 같은 값으로 바꾼다.

## 3. DB · Redis (Docker)

```bash
docker compose up -d db redis
docker compose ps               # db, redis 가 running 이면 OK
```

## 4. 백엔드

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head            # DB 테이블 생성
uvicorn app.main:app --reload   # http://localhost:8000/docs 열리면 성공
```

## 5. 엣지 에이전트 (웹캠 연결 PC)

```bash
cd edge
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m edge.main --camera 0 --bed-id BED-01 --preview   # --preview: 관절 표시 창 (개발용)
```

- 포즈 모델 파일(`pose_landmarker.task`)은 저장소에 없다. MediaPipe 공식 페이지에서 받아 `edge/models/weights/`에 둔다.
- `EDGE_DEVICE_TOKEN`은 백엔드 관리자 화면(또는 `POST /edge-devices`)에서 발급받아 `.env`에 넣는다.
- `--preview` 창은 개발용이다. **녹화 기능을 만들지 않는다** (D-002).

### 카메라 설치 가이드
- 침대 머리맡 위쪽 또는 천장에서 **침대 전체가 보이도록 내려다보는** 각도.
- 역광(창문 정면)을 피하고, 야간 테스트는 IR 카메라로 별도 진행.
- 개발·시연 영상은 **팀원이 직접 누워서 촬영**한다. 실제 환자 촬영 금지.

## 6. 프론트엔드

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## 7. 확인 명령 (PR 올리기 전)

```bash
# backend/, edge/
ruff check . && ruff format --check . && pytest
# frontend/
npm run lint && npm run typecheck && npm run build
```

## 8. 자주 막히는 문제

| 증상 | 해결 |
|------|------|
| `python` 명령이 Microsoft Store를 연다 | 설정 → 앱 실행 별칭에서 python 끄기, 또는 `py -3.11` 사용 |
| 가상환경 활성화가 PowerShell에서 막힘 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| 웹캠이 안 열림 (`--camera 0`) | 다른 앱(Zoom 등)이 쓰는 중인지 확인, `--camera 1`로 시도 |
| DB 연결 실패 | `docker compose ps`로 db 상태 확인, `.env`의 비밀번호가 `DATABASE_URL`과 같은지 확인 |
| 프론트에서 CORS 에러 | `.env`의 `CORS_ORIGINS`에 `http://localhost:5173` 있는지 확인 |
