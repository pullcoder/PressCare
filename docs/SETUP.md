# SETUP — 개발 환경 설치

> Windows 기준으로 쓰고, macOS/Linux 차이는 괄호로 적었습니다.
> 2026-11-04 개정: PostgreSQL·Redis Docker 대신 **Supabase**를 쓴다 (D-009).

## 1. 설치할 프로그램

| 프로그램 | 버전 | 확인 명령 |
|---------|------|----------|
| Git | 최신 | `git --version` |
| Python | **3.11.x** | `python --version` |
| Node.js | 20 LTS 이상 | `node -v`, `npm -v` |
| Supabase CLI | 최신 | `npx supabase --version` (설치 없이 npx로 사용) |
| Docker Desktop | 최신 | `docker --version` — **로컬 Supabase를 띄울 때만** 필요 |
| VS Code | 최신 | 추천 확장: Python, Ruff, ESLint, Prettier, Tailwind CSS IntelliSense |
| 웹캠 | USB 웹캠 1대 (720p 이상) | 카메라 앱으로 화면 나오는지 확인 |

> Python 3.12 이상은 MediaPipe 호환을 확인한 뒤 올린다 (D-005).

## 2. 저장소 받기

```bash
git clone https://github.com/pullcoder/PressCare.git
cd PressCare
cp .env.example .env            # Windows: copy .env.example .env
```

## 3. Supabase 준비

> ⚠️ `supabase/`, `backend/`, `edge/`, `frontend/`는 TASKS T0-3~T0-6에서 만들어진다. 그 전에는 3~6단계 명령이 동작하지 않는다.

### 방법 A. 클라우드 프로젝트 (팀 공용, 기본)
1. [supabase.com](https://supabase.com)에서 프로젝트를 만든다. **Region: Northeast Asia (Seoul)**.
2. Project Settings → API Keys에서 Project URL, **publishable 키**(`sb_publishable_...`), **secret 키**(`sb_secret_...`)를 `.env`에 넣는다. Legacy 탭(anon/service_role, JWT secret)은 쓰지 않는다.
   - Project Settings → JWT Signing Keys에서 현재 키가 **ES256**인지 확인한다. Legacy HS256이면 JWKS가 비어 있어 backend 토큰 검증이 실패한다.
3. 테이블·RLS를 올린다.
```bash
npx supabase login
npx supabase link --project-ref <프로젝트 ref>
npx supabase db push             # supabase/migrations/ 의 SQL 적용
```
- 프로젝트는 **한 명(PM)이 만들고** 키는 팀 비공개 채널로 공유한다. secret 키와 암호화 키(`FIELD_ENCRYPTION_KEY`, `BLIND_INDEX_KEY`)는 backend 담당만.
- 무료 플랜은 오래 쓰지 않으면 일시정지된다. 시연 전날 대시보드에서 상태를 확인한다.

### 방법 B. 로컬 Supabase (개인 실험·인터넷 없는 시연)
```bash
npx supabase start               # Docker 필요. 끝나면 URL·키가 출력됨 → .env 에 넣기
npx supabase db reset            # migrations + seed.sql 다시 적용
npx supabase stop
```
- `supabase/config.toml`의 `[db] major_version`을 클라우드 프로젝트 Postgres 버전과 같게 둔다.
- ⚠️ 로컬 Supabase는 기본으로 HS256 토큰을 발급할 수 있어 JWKS 검증이 실패할 수 있다. `npx supabase gen signing-key --algorithm ES256`로 키를 만들어 `config.toml`의 `[auth] signing_keys_path`에 지정하고, 로그인 후 `/auth/v1/.well-known/jwks.json`에 키가 보이는지 확인한다. 안 되면 T4-1에서 팀과 대응 방법을 정한다.

### 테이블을 바꿀 때
```bash
npx supabase migration new add_guardian_links   # supabase/migrations/<시각>_add_guardian_links.sql 생성
# SQL 작성 후
npx supabase db reset            # 로컬에서 확인
npx supabase db push             # 클라우드 반영 (PR merge 후)
```
- 대시보드에서 테이블을 직접 고치지 않는다. **모든 변경은 마이그레이션 SQL로** 남긴다.

## 4. 백엔드

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs 열리면 성공
```

- 연결 확인: `http://localhost:8000/api/v1/health` → `"supabase": "connected"`. 키를 아직 안 넣었으면 `not_configured`.

## 5. 엣지 에이전트 (웹캠 연결 PC)

```bash
cd edge
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m edge.download_model                                # 처음 한 번: 포즈 모델 받기
python -m edge.main --camera 0 --bed-id BED-01 --preview   # --preview: 관절 표시 창 (개발용)
```

- 포즈 모델 파일(`pose_landmarker_lite.task`)은 저장소에 없다. 처음 한 번 `python -m edge.download_model`을 실행하면 `edge/models/weights/`에 받아진다 (`--variant full`로 더 정확한 모델).
- 종료(`q` 또는 Ctrl+C)할 때 사람 검출률과 주요 관절 평균 신뢰도가 출력된다. 인식 검증(T1-0)에 참고한다.
- `EDGE_DEVICE_TOKEN`은 `POST /edge-devices`(API.md 3장)로 발급받아 `.env`에 넣는다.
- `--preview` 창은 개발용이다. **edge 코드에 녹화·프레임 저장 기능을 만들지 않는다** (D-002).

### 휴대폰을 카메라로 쓰기
- **iPhone + Mac (연속성 카메라)**: 같은 Apple ID로 로그인, Wi-Fi·Bluetooth 켜기, iPhone을 거치대에 고정하면 Mac에 카메라로 잡힌다. `python -m edge.list_cameras`로 번호를 확인해 `--camera <번호>`로 실행한다.
- **그 밖의 휴대폰**: IP 카메라 앱으로 같은 Wi-Fi에 영상을 내보내고 `--camera http://<휴대폰IP>:<포트>/...` 또는 `rtsp://...` 주소를 넣는다. 영상은 같은 공유기 안에서만 오가게 한다 (D-002).

### 카메라 없이 개발하기
```bash
python tools/fake_beds.py --beds 4 --time-scale 60   # 가짜 병상 4개가 자세 이벤트를 보냄
```

### 환경변수 위치
- `.env`는 **저장소 루트에 하나만** 둔다.
- backend·edge 설정 코드는 루트 `.env`를 읽도록 경로를 지정한다 (예: pydantic-settings `env_file="../.env"`).
- frontend는 `vite.config.ts`에 `envDir: '..'`를 넣어야 루트 `.env`의 `VITE_` 변수를 읽는다.
- **`SUPABASE_SERVICE_ROLE_KEY`는 `VITE_`로 시작하는 변수에 절대 넣지 않는다.** (브라우저에 노출되면 RLS가 무력화됨)

### 카메라 설치 가이드
- 위치는 1주차 인식 검증(TASKS T1-0) 결과로 정한다 (D-013). 후보: 천장 바로 위, 발치 위 45°, 침대 옆 위 45°.
- 역광(창문 정면)을 피하고, 야간 테스트는 IR 카메라로 별도 진행.
- 개발·시연 영상은 **팀원이 직접 누워서 촬영**한다. 실제 환자 촬영 금지. 30° 측위(베개로 받친 자세)도 포함한다.
- 테스트 영상은 저장소 밖(예: 팀 드라이브)에 보관한다. `.gitignore`가 `*.mp4` 등을 막지만 다른 확장자도 커밋하지 않는다.

## 6. 프론트엔드

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```
- 경고음은 브라우저 정책상 **페이지에서 한 번 클릭한 뒤에만** 난다. 대시보드의 "알림 켜기" 버튼을 누른다.
- 웹 푸시는 `localhost` 또는 HTTPS에서만 동작한다. 아이폰은 iOS 16.4 이상에서 홈 화면에 추가해야 받는다.

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
| Supabase 연결 실패 | `.env`의 `SUPABASE_URL`·키 확인, 클라우드 프로젝트가 일시정지 상태인지 대시보드에서 확인 |
| 화면에서 데이터가 안 보임 | RLS 정책 확인. 로그인한 계정의 `profiles.ward_id`·`role`이 맞는지 확인 |
| 실시간 갱신이 안 됨 | 테이블이 Realtime publication에 추가됐는지 확인 (`bed_status`, `alerts`) |
| `supabase start` 실패 | Docker Desktop이 실행 중인지 확인 |
| 프론트에서 CORS 에러 | `.env`의 `CORS_ORIGINS`에 `http://localhost:5173` 있는지 확인 |
