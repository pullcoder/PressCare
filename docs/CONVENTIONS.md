# CONVENTIONS — 코딩 · 네이밍 · 주석 규칙

## 1. 공통

- **주석·문서·커밋 메시지는 한국어**, 코드 식별자(변수·함수·클래스·파일명)는 **영어**.
- 주석은 "무엇을"보다 **"왜"**를 쓴다. 코드만 보고 알 수 있는 내용은 쓰지 않는다.
- 매직 넘버 금지: 120(분), 0.6(신뢰도) 같은 값은 설정(`config`)이나 상수로 뺀다.
- 한 함수는 한 가지 일. 50줄이 넘으면 나눌 수 있는지 본다.
- 시간은 **UTC로 저장·계산**, 화면 표시할 때만 `Asia/Seoul`로 바꾼다.

## 2. 이름 짓기

| 대상 | 규칙 | 예시 |
|------|------|------|
| Python 변수·함수 | snake_case | `elapsed_minutes`, `classify_posture()` |
| Python 클래스 | PascalCase | `PostureClassifier`, `MediaPipePoseEstimator` |
| 상수 | UPPER_SNAKE | `DEFAULT_REPOSITION_INTERVAL_MIN` |
| TS 변수·함수 | camelCase | `elapsedMin`, `fetchBedStatus()` |
| React 컴포넌트·파일 | PascalCase | `BedCard.tsx`, `PressureHeatmap.tsx` |
| 훅 | `use` + PascalCase | `useBedStatus.ts` |
| API 경로 | 소문자, 복수형, `-` 연결 | `/posture-events`, `/beds/{bed_id}` |
| DB 테이블 | snake_case 복수형 | `posture_events` |
| 자세 값 | 영어 snake_case 고정 | `left_lateral` (화면에는 "좌측위") |

자세 한글 표시는 한 곳(`frontend/src/shared/constants/posture.ts`, `backend/app/core/postures.py`)에서만 정의한다.

## 3. Python (backend, edge)

- Python 3.11, 타입 힌트 필수 (`def classify(kp: Keypoints) -> PostureResult:`)
- 포맷·린트: **ruff** (`ruff check .`, `ruff format .`), 줄 길이 100
- API 입출력은 Pydantic 스키마로만. 라우터에서 DB 모델을 그대로 반환하지 않는다.
- 라우터(`api/v1/`)는 얇게, 로직은 `services/`에.
- 예외: 직접 정의한 `AppError(code, message, status)`를 던지고 공통 핸들러가 에러 형식으로 바꾼다.
- 로그: `logging` 사용, `print` 금지. **환자 이름·영상·keypoints 원본을 로그에 남기지 않는다.**
- 테스트: `pytest`, 파일명 `test_*.py`. 자세 분류기는 keypoints 픽스처(JSON)로 테스트한다.

## 4. TypeScript / React (frontend)

- 함수형 컴포넌트 + 훅. `any` 금지 (불가피하면 이유 주석).
- 기능별 폴더(`features/<기능>/`): 컴포넌트, 훅, api 호출을 기능 안에 모은다.
- 서버 호출은 `shared/api/` 클라이언트를 통해서만. 컴포넌트에서 `fetch` 직접 호출 금지.
- 스타일: Tailwind. 상태 색상은 의미로 고정 → ok=초록, warning=노랑, critical=빨강, unknown/offline=회색.
- 린트·포맷: ESLint + Prettier (`npm run lint`).

## 5. 3D (viewer3d)

- 인체 모델은 `.glb`, 부위는 메시 이름을 API 부위 키와 같게 (`sacrum`, `heel_left` ...).
- 히트맵 색: 강도 0 → 원래 색, 1 → 빨강. 색 계산은 한 함수에 모은다.
- 화면에 "실제 압력 측정값이 아님" 안내를 항상 표시한다.

## 6. 문구 (UI·문서)

- "진단", "욕창 발생 확률", "위험도 예측" 같은 의료 판단 표현 쓰지 않기 → "체위 유지 시간", "체위변경 필요" 사용. (D-003)
- 환자는 화면에서 가명/이니셜(`이○○`)로 표시.
