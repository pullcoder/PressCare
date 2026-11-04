# PressCare

> 욕창 예방을 위한 **체위변경 자동 인식 + 3D 압박 부위 모니터링** 서비스

병상 위 웹캠 한 대로 환자의 자세를 비접촉으로 인식하고, 같은 자세가 오래 이어지면
간호 인력에게 알려 주며, 오래 눌린 부위를 3D 아바타 위에 히트맵으로 보여주는 웹 서비스입니다.
간호사·관리자·보호자는 설치 없이 웹(PWA)으로 접속하고, 병상에는 인식 프로그램만 설치합니다.
센서 부착이나 고가의 스마트 베드 없이 **카메라 + 소프트웨어**만으로 동작하는 것이 목표입니다.

```
카메라 영상 → 자세 추정(Pose) → 5가지 자세 분류 → 자세 유지 시간 측정 → 2시간 초과 알림 + 3D 압박 히트맵
```

## 핵심 기능

| # | 기능 | 한 줄 설명 |
|---|------|-----------|
| ① | AI 자세 분류 | 앙와위 / 좌측위 / 우측위 / 앉음 / 부재 5가지 자동 분류 |
| ② | 체위 타이머·자동 기록 | 자세가 바뀌면 자동 기록, 같은 자세 유지 시간 측정 (간호 기록 대체) |
| ③ | 실시간 알림 | 기준 시간(기본 120분) 초과 시 대시보드 경고음 → 스마트폰 웹 푸시 → 미확인 시 문자 |
| ④ | 3D 압박 부위 시각화 | 둔부·뒤꿈치·어깨 등 오래 눌린 부위를 3D 아바타 위 붉은 히트맵으로 표시 |
| ⑤ | 이불·야간 대응 | 이불을 덮거나 어두워도 인식되도록 보정 알고리즘 / IR 카메라 연동 (후순위) |

자세한 기획은 [docs/PLAN.md](docs/PLAN.md)를 보세요.

## 기술 스택

- **Edge (병상 PC)**: Python 3.11, OpenCV, MediaPipe Pose (YOLO-Pose는 라이선스 검토 후, D-004)
- **Backend**: Python 3.11, FastAPI (이벤트 수신, 타이머·알림 판단, 문자·웹 푸시 발송)
- **Data**: Supabase — PostgreSQL, Auth(로그인), RLS(권한), Realtime(실시간 갱신), 서울 리전 (D-009~D-011)
- **Frontend**: React + TypeScript (Vite), Tailwind CSS, supabase-js, Three.js + React Three Fiber (3D 히트맵), PWA

## 폴더 구조 (요약)

```
PressCare/
├── edge/            # 병상 카메라 → 자세 추론 에이전트 (영상은 여기서만 처리)
├── backend/         # FastAPI 서버 (자세 이벤트 저장, 타이머, 알림)
├── frontend/        # React 웹앱 (간호사·관리자·보호자 화면, 3D 뷰어)
├── supabase/        # 테이블·RLS 마이그레이션 SQL, 시연용 seed
├── tools/           # 가짜 병상 시뮬레이터 등 개발 도구
├── docs/            # 기획·설계·규칙 문서
├── AGENTS.md        # AI 코딩 도구 공통 지시서 (Codex 등)
├── CLAUDE.md        # Claude Code 지시서 (AGENTS.md를 불러옴)
└── .env.example     # 환경변수 예시
```

전체 구조는 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)에 있습니다.

## 빠른 실행

> 처음이라면 [docs/SETUP.md](docs/SETUP.md)부터 따라 하세요.
> ⚠️ 아직 코드 뼈대가 없어서 아래 명령은 `supabase/`, `edge/`, `backend/`, `frontend/`가 추가된 뒤(TASKS T0-3~T0-6)부터 동작합니다.

```bash
# 0) 환경변수
cp .env.example .env            # Windows PowerShell: copy .env.example .env
                                # Supabase URL·키를 채운다 (SETUP.md 3장)

# 1) DB 테이블 반영 (Supabase 클라우드 프로젝트)
npx supabase link --project-ref <프로젝트 ref>
npx supabase db push            # 로컬로 하려면: npx supabase start (Docker 필요)

# 2) 백엔드
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 3) 엣지 에이전트 (새 터미널, 웹캠 연결된 PC)
cd edge
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m edge.main --camera 0 --bed-id BED-01

# 4) 프론트엔드 (새 터미널)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## 문서 안내

| 문서 | 내용 |
|------|------|
| [PLAN.md](docs/PLAN.md) | 기획 요약, 기능 명세 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 구조, 폴더 구조, DB 개요 |
| [API.md](docs/API.md) | REST API · Supabase 조회·Realtime 명세 |
| [CONVENTIONS.md](docs/CONVENTIONS.md) | 코딩·네이밍·주석 규칙 |
| [GIT_GUIDE.md](docs/GIT_GUIDE.md) | Git 사용법과 협업 흐름 |
| [SETUP.md](docs/SETUP.md) | 개발 환경 설치 |
| [TASKS.md](docs/TASKS.md) | 단계별 할 일, 담당자 |
| [DECISIONS.md](docs/DECISIONS.md) | 주요 결정과 이유 |

## 팀

팀원과 역할은 [docs/TASKS.md](docs/TASKS.md#팀-역할)에서 관리합니다.
