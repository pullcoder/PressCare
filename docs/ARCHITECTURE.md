# ARCHITECTURE — 시스템 구조 · 폴더 구조

## 1. 전체 구조

```
[병상 웹캠/IR 카메라]
        │ 영상 (병상 PC 밖으로 나가지 않음)
        ▼
┌──────────────────────────┐
│ edge/  (병상 PC, Python)  │
│ 프레임 캡처 → 포즈 추정    │
│ → 자세 분류 → 안정화 필터  │
└──────────┬───────────────┘
           │ HTTPS: 자세 라벨 + 신뢰도 + keypoints + 시각
           ▼
┌──────────────────────────┐        ┌────────────┐
│ backend/ (FastAPI)        │◀──────▶│ PostgreSQL │ 환자·병상·자세 이벤트·알림 기록
│ 이벤트 저장, 타이머 계산,  │        └────────────┘
│ 알림 판단, 압박 누적 계산  │◀──────▶┌────────────┐
└──────────┬───────────────┘        │ Redis      │ 병상별 현재 상태, 알림 큐
           │ REST + WebSocket       └────────────┘
           ▼
┌──────────────────────────┐
│ frontend/ (React)         │ 병동 대시보드, 병상 상세, 3D 히트맵, 웹 푸시
└──────────────────────────┘
```

### 왜 edge에서 추론하나? (D-002)
- 환자 영상을 네트워크로 보내지 않아 **개인정보 위험이 가장 작다**.
- 서버 부하·대역폭이 줄어든다 (영상 대신 수십 바이트 JSON).

## 2. 데이터 흐름

1. edge가 `CAMERA_FPS`로 프레임을 읽는다.
2. `PoseEstimator`(인터페이스)가 관절 좌표 33개(MediaPipe 기준)를 반환한다.
3. `PostureClassifier`가 좌표로 자세 라벨 + 신뢰도를 계산한다.
4. `StabilityFilter`가 `POSTURE_STABLE_SEC` 동안 같은 라벨이면 **자세 확정**.
5. 확정 시(그리고 1분마다 heartbeat) `POST /edge/posture-events` 전송.
6. backend가 이벤트 저장 → 현재 자세 유지 시간 갱신 → 기준 초과 시 `alerts` 생성 → WebSocket·웹 푸시.
7. frontend가 WebSocket으로 병상 상태를 받아 대시보드·3D 히트맵을 갱신한다.

## 3. 폴더 구조

```
PressCare/
├── edge/
│   ├── edge/
│   │   ├── main.py              # 진입점: 카메라 루프
│   │   ├── capture.py           # 웹캠/RTSP 프레임 읽기
│   │   ├── pose/
│   │   │   ├── base.py          # PoseEstimator 인터페이스
│   │   │   └── mediapipe_pose.py
│   │   ├── classify/
│   │   │   ├── posture.py       # 좌표 → 5가지 자세
│   │   │   └── stability.py     # 깜빡임 방지 필터
│   │   ├── client.py            # backend API 호출
│   │   └── config.py
│   ├── tests/
│   └── requirements.txt
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                # 설정, 보안, DB 세션
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── wards.py         # 병동·병상
│   │   │   ├── patients.py
│   │   │   ├── edge.py          # 엣지 이벤트 수신
│   │   │   ├── postures.py      # 자세 이력·타임라인
│   │   │   ├── alerts.py
│   │   │   ├── pressure.py      # 압박 누적(히트맵 데이터)
│   │   │   └── ws.py            # WebSocket
│   │   ├── models/              # SQLAlchemy 모델
│   │   ├── schemas/             # Pydantic 스키마
│   │   ├── services/            # 타이머·알림·압박 계산 로직
│   │   └── workers/             # 주기 작업 (알림 체크)
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # 라우팅, 레이아웃
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── dashboard/       # 병동 전체 병상 카드
│   │   │   ├── bed/             # 병상 상세, 타임라인
│   │   │   ├── viewer3d/        # Three.js 압박 히트맵
│   │   │   └── alerts/          # 알림 목록, 웹 푸시
│   │   ├── shared/              # 공용 컴포넌트, api 클라이언트, 훅
│   │   └── main.tsx
│   ├── public/models/           # 3D 인체 모델 (.glb)
│   └── package.json
├── docs/
├── docker-compose.yml           # db, redis
└── .env.example                 # 환경변수는 루트 .env 하나만 사용
```

## 4. DB 개요 (초안)

| 테이블 | 주요 컬럼 | 설명 |
|--------|----------|------|
| `users` | id, email, password_hash, name, role(`admin`/`nurse`/`guardian`), ward_id(nullable) | 사용자 (간호사는 소속 병동만 조회) |
| `wards` | id, name | 병동 |
| `beds` | id, ward_id, code(`BED-01`), patient_id(nullable) | 병상 |
| `patients` | id, display_name(가명/이니셜), reposition_interval_min(nullable, 환자별 기준) | 환자 (실명 최소화) |
| `edge_devices` | id, bed_id, token_hash, last_seen_at | 병상 PC |
| `posture_events` | id, bed_id, posture, confidence, keypoints(JSONB), started_at, source(`edge`/`manual`) | 확정된 자세 변경 |
| `alerts` | id, bed_id, level(`warning`/`critical`), triggered_at, acknowledged_by, acknowledged_at | 알림 |
| `push_subscriptions` | id, user_id, endpoint, p256dh, auth, created_at | 웹 푸시 구독 |
| `pressure_snapshots` | id, bed_id, date, region_seconds(JSONB) | 부위별 누적 압박 시간 (히트맵용) |

- 시각은 모두 **UTC로 저장**, 화면에서 `Asia/Seoul`로 표시.
- 보호자(`guardian`)의 환자 연결 방식은 v1에서 정한다 (MVP는 `admin`/`nurse`만).
- 스키마가 바뀌면 Alembic 마이그레이션 + 이 표 갱신.

## 5. 자세 분류 로직 (MVP 규칙 기반)

| 판단 | 근거 (MediaPipe 관절) |
|------|----------------------|
| `absent` | 사람 미검출이 `POSTURE_STABLE_SEC` 이상 |
| `sitting` | 어깨–엉덩이 선이 수직에 가깝고 엉덩이–무릎 각도 ≈ 90° |
| `supine` | 양 어깨·양 엉덩이가 카메라 기준 좌우로 넓게 보이고 코가 위를 향함 |
| `left_lateral` / `right_lateral` | 어깨 폭이 좁게 보이고(겹침) 몸통 방향 벡터로 좌/우 판단 |
| `unknown` | 주요 관절 신뢰도 < `POSTURE_MIN_CONFIDENCE` |

> 카메라는 침대 위(천장/머리맡 위쪽)에서 내려다보는 위치를 기준으로 한다. 설치 각도는 SETUP.md 참고.
> 규칙으로 부족하면 keypoints 기반 경량 분류기(예: scikit-learn)로 교체한다 → DECISIONS에 기록.
