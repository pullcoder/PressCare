# AGENTS.md — AI 코딩 도구 공통 지시서

이 파일은 Codex 등 AI 코딩 에이전트가 이 저장소에서 작업할 때 따르는 **공통 규칙**입니다.
Claude Code는 `CLAUDE.md`에서 이 파일을 그대로 불러오므로, 공통 규칙은 **여기 한 곳에서만** 고칩니다.

## 1. 프로젝트 한 줄 요약

PressCare: 병상 웹캠 영상으로 환자 자세를 5가지(앙와위·좌측위·우측위·앉음·부재)로 비접촉 분류하고,
같은 자세 유지 시간이 기준(기본 120분)을 넘으면 간호 인력에게 알리며, 오래 눌린 부위를 3D 아바타 히트맵으로 보여주는 서비스.
현재 단계 범위는 `docs/TASKS.md`를 따른다.

## 2. 작업 전에 읽을 문서

| 상황 | 먼저 읽을 문서 |
|------|---------------|
| 기능을 새로 만든다 | `docs/PLAN.md`, `docs/TASKS.md` |
| 파일 위치·구조를 정한다 | `docs/ARCHITECTURE.md` |
| API·Supabase 조회·Realtime을 만들거나 호출한다 | `docs/API.md` |
| 코드를 쓴다 (항상) | `docs/CONVENTIONS.md` |
| 커밋·브랜치·PR | `docs/GIT_GUIDE.md` |
| 설치·실행 | `docs/SETUP.md` |
| "왜 이렇게 했지?" | `docs/DECISIONS.md` |

문서와 코드가 다르면 **코드를 문서에 맞추지 말고 먼저 사용자에게 알린다.**

## 3. 기술 스택 (임의로 바꾸지 않기)

- Edge: Python 3.11, OpenCV, MediaPipe Pose — 영상 처리·자세 추론은 **edge/에서만**
- Backend: Python 3.11, FastAPI, Pydantic v2, supabase-py — 이벤트 수신·타이머·알림 판단은 **backend에서만** (D-010)
- Data: Supabase (PostgreSQL, Auth, RLS, Realtime) — Redis·자체 WebSocket·자체 JWT 로그인·Alembic은 쓰지 않는다 (D-009, D-011)
- Frontend: React + TypeScript (Vite), Tailwind CSS, supabase-js, Three.js + React Three Fiber, PWA (네이티브 앱 없음)

새 라이브러리 추가, 스택 변경, 폴더 구조 변경은 **사용자 확인 후** 진행하고 `docs/DECISIONS.md`에 기록한다.

## 4. 반드시 지킬 규칙

1. **작은 단위로 작업한다.** 한 번에 한 기능·한 버그. 요청과 관계없는 파일은 고치지 않는다.
2. **비밀 정보 금지.** API 키, 비밀번호, 토큰을 코드·문서·커밋에 넣지 않는다. `.env`만 사용하고, 새 변수는 `.env.example`에 빈 값으로 추가한다.
   - `SUPABASE_SERVICE_ROLE_KEY`는 RLS를 무시하는 키다. **backend에서만** 쓰고, frontend 코드나 `VITE_` 변수에 절대 넣지 않는다.
   - frontend는 Supabase 테이블을 **읽기만** 한다. 쓰기는 backend API를 거친다.
3. **환자 영상은 밖으로 내보내지 않는다.** (D-002)
   - 원본 영상·프레임은 edge 메모리에서만 처리하고 디스크에 저장하지 않는다 (`SAVE_RAW_FRAMES=false`가 기본값).
   - 서버로 보내는 것은 **자세 라벨, 신뢰도, 관절 좌표(keypoints), 시각**뿐이다.
   - 환자 이름·영상·사진을 로그에 남기지 않는다. 환자는 `patient_id`/`bed_id`로만 다룬다.
   - 테스트·데모에는 실제 환자 영상 대신 팀원이 직접 찍은 영상이나 공개 데이터셋만 쓴다.
4. **진단하지 않는다.** 화면 문구·코드 주석·문서에서 "욕창 진단/예측 확률"처럼 의료 판단으로 읽히는 표현을 쓰지 않는다. 이 서비스는 **체위변경 기록·알림 보조 도구**다. (D-003)
5. **AI 모델 라이선스.** 새 모델·가중치를 넣기 전에 상업적 이용 가능 여부를 확인하고 `docs/DECISIONS.md`에 적는다. **Ultralytics YOLOv8/YOLO11은 AGPL-3.0이므로 확인 전에는 넣지 않는다.** 포즈 추정기는 교체 가능한 인터페이스 뒤에 둔다. (D-004)
6. **기준 시간·임계값은 하드코딩하지 않는다.** 체위변경 주기(`REPOSITION_INTERVAL_MIN`, 기본 120), 사전 경고(`REPOSITION_WARNING_MIN`, 기본 100), 자세 확정 시간(`POSTURE_STABLE_SEC`), offline 판정(`EDGE_OFFLINE_SEC`) 등은 설정에서 읽는다. `DEMO_TIME_SCALE`은 시연 전용이며 production에서는 항상 1로 동작해야 한다.
7. **API를 바꾸면 `docs/API.md`도 같이 고친다.** DB 스키마·RLS를 바꾸면 `supabase/migrations/`에 SQL 마이그레이션(`npx supabase migration new <이름>`)을 만들고 `docs/ARCHITECTURE.md` 7장을 갱신한다. Supabase 대시보드에서 테이블을 직접 고치지 않는다.
   - 새 테이블은 **RLS를 켠 상태로** 만든다. 정책 없이 열어 두지 않는다.
8. **main 브랜치에 직접 커밋·푸시하지 않는다.** `feature/...` 등 브랜치에서 작업한다. (`docs/GIT_GUIDE.md`)
9. **주석과 문서는 한국어**, 코드 식별자(변수·함수·파일명)는 영어.

## 5. 완료 전 확인 (Definition of Done)

```bash
# backend/, edge/
ruff check . && ruff format --check . && pytest

# supabase/ (스키마를 바꿨을 때)
npx supabase db reset            # 로컬에서 마이그레이션이 처음부터 적용되는지 확인

# frontend/
npm run lint && npm run typecheck && npm run build
```

- 위 명령이 통과하지 못하면 "완료"라고 하지 말고 실패 내용을 그대로 보고한다.
- 아직 해당 명령이 설정되지 않았다면, 실행하지 못했다고 명시한다.
- 작업 끝에 **변경한 파일 목록과 이유**를 짧게 요약한다.

## 6. 하지 말 것

- `.env`, 녹화 영상(`*.mp4`, `*.avi`), `recordings/`, 모델 가중치(`*.pt`, `*.onnx`, `*.task`) 커밋
- 테스트를 지우거나 건너뛰게(skip) 만들어 통과시키기
- `git push --force`, `git reset --hard` 등 되돌리기 어려운 명령을 사용자 확인 없이 실행
- 사용자가 요청하지 않은 대규모 리팩터링·포맷 변경
