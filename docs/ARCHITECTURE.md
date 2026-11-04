# ARCHITECTURE — 시스템 구조 · 폴더 구조

> 2026-11-04 개정: DB를 **Supabase**(PostgreSQL·Auth·Realtime)로 바꾸고 Redis·자체 WebSocket·Alembic을 뺐다. (D-009~D-012)

## 1. 전체 구조

```
[병상 웹캠/IR 카메라]
        │ 영상 (병상 PC 밖으로 나가지 않음)
        ▼
┌──────────────────────────┐
│ edge/  (병상 PC, Python)  │  ← 병상에 설치하는 유일한 프로그램
│ 프레임 캡처 → 포즈 추정    │
│ → 자세 분류 → 안정화 필터  │
└──────────┬───────────────┘
           │ HTTPS: 자세 라벨 + 신뢰도 + keypoints + 시각
           ▼
┌──────────────────────────┐   service key   ┌──────────────────────────────┐
│ backend/ (FastAPI, 클라우드)│──────────────▶│ Supabase (서울 리전)           │
│ 이벤트 수신, 타이머·알림 판단│               │ PostgreSQL: 병상·자세·알림 기록 │
│ 압박 누적 계산, 문자 발송   │               │ Auth: 로그인 / RLS: 권한        │
└──────────┬───────────────┘               │ Realtime: 테이블 변경 푸시       │
           │ REST (조회·명령)                 └──────────────┬───────────────┘
           ▼                                                │ Realtime 구독 (bed_status, alerts)
┌──────────────────────────────────────────────────────────┴┐
│ frontend/ (React 웹앱, PWA, Vercel)                          │
│ 간호사 대시보드 · 병상 상세 · 3D 히트맵 · 관리자 설정 · 보호자 화면 │
└────────────────────────────────────────────────────────────┘
```

### 역할 나눔
| 구성 요소 | 맡는 일 | 맡지 않는 일 |
|-----------|--------|-------------|
| edge | 영상 처리, 자세 확정, 이벤트·heartbeat 전송 | DB 직접 접근, 영상 전송·저장 |
| backend (FastAPI) | edge 이벤트 수신, `bed_status` 갱신, 알림 판단(주기 루프), 압박 누적 계산, 문자 발송, 기기 토큰 관리 | 로그인 구현(→ Supabase Auth) |
| Supabase | 데이터 저장, 로그인, 행 단위 권한(RLS), 실시간 변경 전달 | 비즈니스 로직 |
| frontend | 역할별 화면, 실시간 구독, 경고음·웹 푸시 수신 | 알림 판단 (서버가 정한 상태만 표시) |

### 왜 edge에서 추론하나? (D-002)
- 환자 영상을 네트워크로 보내지 않아 **개인정보 위험이 가장 작다**.
- 서버 부하·대역폭이 줄어든다 (영상 대신 수십 바이트 JSON).
- Supabase에도 **라벨·좌표·시각만** 저장한다.

## 2. 데이터 흐름

1. edge가 `CAMERA_FPS`로 프레임을 읽는다.
2. `PoseEstimator`(인터페이스)가 관절 좌표 33개(MediaPipe 기준)를 반환한다.
3. `PostureClassifier`가 좌표로 자세 라벨 + 신뢰도를 계산한다.
4. `StabilityFilter`가 `POSTURE_STABLE_SEC` 동안 같은 라벨이면 **자세 확정**.
5. 확정 시(그리고 1분마다 heartbeat) `POST /edge/posture-events`로 backend에 전송.
6. backend가 `posture_events`에 저장하고 `bed_status`(현재 자세, `posture_since`)를 갱신한다.
7. backend 알림 루프(`ALERT_CHECK_SEC`, 기본 3초)가 경과 시간을 보고 `alerts`를 만들고 `bed_status.status`를 바꾼다. 3초 확인 + Realtime 전달을 합쳐도 PLAN 8장의 "알림 지연 ≤ 5초"를 지키기 위한 값이다.
8. Supabase Realtime이 `bed_status`·`alerts` 변경을 열려 있는 모든 화면에 보낸다.
9. 알림이 `ALERT_ESCALATE_MIN`(기본 5분) 동안 확인되지 않으면 backend가 문자를 보낸다. (D-012)

### 시간은 어떻게 저장하나
- 타이머 값을 매초 저장하지 않는다. **자세 시작 시각(`posture_since`)만 저장**한다.
- 화면은 `지금 - posture_since`로 경과 시간을 계산한다. 어디서 보든 같은 값이 나온다.
- 모든 시각은 UTC(`timestamptz`)로 저장하고 화면에서 `Asia/Seoul`로 표시한다.

## 3. 알림 전달 (3단계)

| 단계 | 언제 | 어디로 | 비고 |
|------|------|-------|------|
| 1. 대시보드 | warning(100분)·critical(120분) | 간호스테이션 PC 브라우저 | 화면 깜빡임 + critical은 확인할 때까지 경고음 반복. 근무 시작 시 "알림 켜기" 클릭 필요(브라우저 자동재생 제한) |
| 2. 웹 푸시 | critical | 간호사·보호자 스마트폰 (PWA) | 안드로이드 Chrome 지원. iOS는 16.4 이상 + 홈 화면 추가 시에만 |
| 3. 문자 | critical 후 `ALERT_ESCALATE_MIN` 동안 미확인 | 담당 간호사·보호자 휴대폰 | 문자 API(예: Solapi). 카카오 알림톡은 사업화 단계 |

## 4. 사용자와 화면

웹앱 하나에서 로그인한 사람의 역할(`profiles.role`)에 따라 화면이 달라진다.

| 역할 | 화면 | 볼 수 있는 범위 (RLS) | 단계 |
|------|------|---------------------|------|
| `admin` 병원 관리자 | 병동·병상·기기 등록, 계정·권한, 환자별 기준 시간 | 병원 전체 | MVP(최소) |
| `nurse` 간호사·요양보호사 | 병동 대시보드, 병상 상세·타임라인, 알림 확인, 수동 기록, 3D 히트맵 | 소속 병동 | MVP |
| `head_nurse` 수간호사 | 수행률·누락 통계, 기록 내보내기 | 담당 병동 | v1 |
| `guardian` 보호자 | 가족 1명의 현재 자세, 오늘 체위변경 횟수·시각 (영상 없음) | 연결된 환자 1명 | v1 (MVP는 시연용 화면 1장) |
| `doctor` 의사·방문간호사 | 환자 이력 읽기 전용 | 담당 환자 | v2 |

## 5. 배포

| 구성 요소 | 운영 위치 | 공모전 시연 |
|-----------|----------|------------|
| edge | 병상 옆 미니PC·노트북 + 웹캠 (설치형, 이후 PyInstaller로 exe) | 노트북 |
| backend | 클라우드 (Render·Fly.io 또는 AWS 서울) | 노트북 로컬 또는 클라우드 |
| Supabase | 클라우드, 서울 리전(`ap-northeast-2`) | 클라우드. 현장 인터넷이 불안하면 Supabase CLI 로컬로 전환 |
| frontend | Vercel 등 정적 호스팅 (PWA) | 클라우드 주소로 접속 |

- 앱스토어용 네이티브 앱은 만들지 않는다 (D-008).
- 외부 클라우드를 허용하지 않는 병원은 사업화 단계에서 Supabase 셀프 호스팅 + backend를 병원 내부 서버에 설치하는 방식으로 대응한다.

## 6. 폴더 구조

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
│   │   ├── core/                # 설정, Supabase 클라이언트, JWT 검증, crypto.py(암호화·해시)
│   │   ├── api/v1/
│   │   │   ├── edge.py          # 엣지 이벤트·heartbeat 수신
│   │   │   ├── devices.py       # 기기 토큰 발급·폐기
│   │   │   ├── postures.py      # 타임라인, 수동 기록
│   │   │   ├── alerts.py        # 알림 확인(ack)
│   │   │   ├── pressure.py      # 압박 누적(히트맵 데이터)
│   │   │   └── push.py          # 웹 푸시 구독
│   │   ├── schemas/             # Pydantic 스키마
│   │   ├── services/            # 타이머·알림·압박 계산, 문자·푸시 발송
│   │   └── workers/             # 알림 판단 루프
│   ├── tests/
│   └── requirements.txt
├── supabase/
│   ├── config.toml              # 로컬 Supabase 설정 (Postgres 메이저 버전을 클라우드와 맞춤)
│   ├── migrations/              # 테이블·RLS 정책 SQL (스키마 변경은 여기서만)
│   └── seed.sql                 # 시연용 병동·병상·계정
├── tools/
│   └── fake_beds.py             # 가짜 병상 시뮬레이터 (카메라 없이 이벤트 전송)
├── frontend/
│   ├── src/
│   │   ├── app/                 # 라우팅, 레이아웃, 역할별 메뉴
│   │   ├── features/
│   │   │   ├── auth/            # Supabase Auth 로그인
│   │   │   ├── dashboard/       # 병동 전체 병상 카드
│   │   │   ├── bed/             # 병상 상세, 타임라인
│   │   │   ├── viewer3d/        # Three.js 압박 히트맵
│   │   │   ├── alerts/          # 알림 목록, 경고음, 웹 푸시
│   │   │   ├── admin/           # 병상·기기·계정 관리
│   │   │   └── guardian/        # 보호자 화면
│   │   ├── shared/              # 공용 컴포넌트, api·supabase 클라이언트, 훅
│   │   └── main.tsx
│   ├── public/models/           # 3D 인체 모델 (.glb)
│   └── package.json
├── docs/
└── .env.example                 # 환경변수는 루트 .env 하나만 사용
```

## 7. DB 개요 (Supabase PostgreSQL, 초안)

| 테이블 | 주요 컬럼 | 설명 |
|--------|----------|------|
| `profiles` | id(= `auth.users.id`), name, role(`admin`/`head_nurse`/`nurse`/`guardian`/`doctor`), ward_id(nullable), phone_enc, phone_bidx, contact_email_enc, contact_email_bidx, address_enc (모두 nullable) | 사용자 정보. 로그인·비밀번호는 Supabase Auth. 연락처·주소는 암호화 저장 (D-015, SECURITY.md) |
| `wards` | id, name | 병동 |
| `beds` | id, ward_id, code(`BED-01`), patient_id(nullable) | 병상 |
| `patients` | id, display_name(가명/이니셜), reposition_interval_min(nullable) | 환자 (실명 최소화) |
| `guardian_links` | guardian_id, patient_id | 보호자 ↔ 환자 연결 (v1) |
| `edge_devices` | id, bed_id, token_hash(SHA-256), last_seen_at, revoked_at | 병상 PC. 토큰 원문은 저장 안 함 (D-016) |
| `bed_status` | bed_id(PK), current_posture, confidence, posture_since, status(`ok`/`warning`/`critical`/`unknown`/`offline`), updated_at | **현재 상태 1행/병상**. Realtime 구독 대상 |
| `posture_events` | id, bed_id, posture, confidence, keypoints(jsonb), started_at, source(`edge`/`manual`), created_by(nullable) | 확정된 자세 변경 이력 |
| `alerts` | id, bed_id, level(`warning`/`critical`), triggered_at, acknowledged_by, acknowledged_at, escalated_at | 알림. Realtime 구독 대상 |
| `push_subscriptions` | id, user_id, endpoint, p256dh, auth, created_at | 웹 푸시 구독 |
| `pressure_snapshots` | id, bed_id, date, region_seconds(jsonb) | 부위별 누적 압박 시간 (히트맵용) |

- 쓰기: edge 이벤트·알림·`bed_status`는 **backend만** 쓴다(service key). 화면은 읽기 + 알림 확인·수동 기록만(backend API 경유).
- RLS: 모든 테이블에 켠다. `nurse`는 `profiles.ward_id`가 같은 병상만, `guardian`은 `guardian_links`의 환자만 읽는다.
- 데이터별 보호 방식 전체는 **`docs/SECURITY.md`**가 기준이다.
- 개인정보 필드(휴대폰·주소·연락용 이메일)는 backend가 **AES-256-GCM으로 암호화**해 `*_enc`(bytea)에 저장하고, 검색·중복 확인은 **HMAC-SHA256 값** `*_bidx`로 한다. 키는 `.env`의 `FIELD_ENCRYPTION_KEY`, `BLIND_INDEX_KEY` (D-015). 화면에는 backend API가 복호화해 필요한 사람에게만 보여준다.
- 스키마가 바뀌면 `supabase/migrations/`에 SQL 마이그레이션을 추가하고 이 표를 갱신한다.

## 8. 자세 분류 로직 (MVP 규칙 기반)

| 판단 | 근거 (MediaPipe 관절) |
|------|----------------------|
| `absent` | 사람 미검출이 `POSTURE_STABLE_SEC` 이상 |
| `sitting` | 어깨–엉덩이 선이 수직에 가깝고 엉덩이–무릎 각도 ≈ 90° |
| `supine` | 양 어깨·양 엉덩이가 카메라 기준 좌우로 넓게 보이고 코가 위를 향함 |
| `left_lateral` / `right_lateral` | 어깨 폭이 좁게 보이고(겹침) 몸통 방향 벡터로 좌/우 판단. **30° 측위도 측위로 분류**한다 |
| `unknown` | 주요 관절 신뢰도 < `POSTURE_MIN_CONFIDENCE` |

> 간호 실무지침은 90° 측위 대신 베개로 받친 **30° 측위**를 권한다. 위에서 보면 앙와위와 비슷해 가장 헷갈리는 자세이므로 1주차 인식 검증(TASKS T1-0)에 반드시 포함한다.
> 카메라 위치는 1주차 검증 결과로 정한다(D-013 예정). 규칙으로 부족하면 keypoints 기반 경량 분류기(scikit-learn)로 교체한다.
