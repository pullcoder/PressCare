# API — REST · Realtime 명세

> 2026-11-04 개정: 로그인은 Supabase Auth, 실시간은 Supabase Realtime으로 바꿨다 (D-009~D-011). 자체 `/auth/login`, WebSocket은 없앴다.

## 0. 어디로 요청하나

| 하는 일 | 어디로 | 인증 |
|--------|-------|------|
| 로그인·로그아웃 | Supabase Auth (`supabase.auth.signInWithPassword`) | 이메일 + 비밀번호 |
| **조회** (병상 상태, 타임라인, 알림 목록, 환자) | Supabase 테이블 직접 조회 (`supabase.from(...)`) | Supabase 세션, **RLS가 범위 제한** |
| **실시간 갱신** | Supabase Realtime 구독 (7장) | Supabase 세션 |
| **쓰기·명령** (edge 이벤트, 알림 확인, 수동 기록, 기기 토큰, 푸시 구독) | FastAPI `/api/v1` | 사용자: `Authorization: Bearer <Supabase access token>` / 엣지: `X-Device-Token` |
| 계산이 필요한 조회 (압박 히트맵, 기록 내보내기) | FastAPI `/api/v1` | 사용자 토큰 |

- 화면은 Supabase 테이블에 **직접 쓰지 않는다.** 쓰기는 모두 FastAPI를 거친다 (RLS로 insert/update 막음).
- FastAPI는 Supabase 사용자 토큰(ES256)을 **공개키(JWKS)로 검증**하고 `profiles`에서 역할을 읽는다 (D-014).
  - JWKS 주소: `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. 토큰 헤더의 `kid`로 키를 고르고, 키 목록은 메모리에 캐시한다(모르는 `kid`가 오면 한 번 다시 받기).
  - 확인할 것: 서명, `exp`, `aud = "authenticated"`, `iss = {SUPABASE_URL}/auth/v1`. `sub`가 사용자 id다.
  - `SUPABASE_JWT_SECRET`(Legacy HS256)은 쓰지 않는다.
- 형식: JSON, 시각은 ISO 8601 UTC (`2026-11-02T06:30:00Z`).
- 실제 동작 명세는 서버 실행 후 `http://localhost:8000/docs`(Swagger)가 기준. **API를 바꾸면 이 문서도 같이 고친다.**

## 공통 에러 형식 (FastAPI)

```json
{ "error": { "code": "BED_NOT_FOUND", "message": "병상을 찾을 수 없습니다." } }
```

| HTTP | 언제 |
|------|------|
| 400 | 입력 형식 오류 |
| 401 | 인증 없음/만료 |
| 403 | 권한 없음 (다른 병동 등) |
| 404 | 대상 없음 |
| 409 | 중복 (이미 확인된 알림 등) |

## 자세 값 (`posture`)

`supine` · `left_lateral` · `right_lateral` · `sitting` · `absent` · `unknown`
(30° 측위는 `left_lateral`/`right_lateral`로 분류)

## 상태 값 (`status`)

`ok` · `warning`(100분) · `critical`(120분) · `unknown` · `offline`

---

## 1. 로그인 (Supabase Auth)

```ts
// frontend
const { data, error } = await supabase.auth.signInWithPassword({ email, password });
// 이후 FastAPI 호출 시
headers: { Authorization: `Bearer ${data.session.access_token}` }
```

### `GET /me` (FastAPI) → 현재 사용자와 역할
```json
{ "id": "6f1c...", "name": "김간호", "role": "nurse", "ward_id": 1 }
```

---

## 2. 조회 (Supabase 직접, RLS 적용)

### 병동 대시보드: `bed_status` + `beds` + `patients`
```ts
supabase.from("bed_status")
  .select("bed_id, current_posture, confidence, posture_since, status, updated_at, beds!inner(code, ward_id, patients(display_name))")
  .eq("beds.ward_id", wardId);
// !inner 가 없으면 다른 병동 병상도 전부 나오고 beds 값만 null 이 된다. 병동 필터에는 반드시 !inner 를 붙인다.
```
```json
[
  {
    "bed_id": 3,
    "current_posture": "supine",
    "confidence": 0.91,
    "posture_since": "2026-11-02T04:40:00Z",
    "status": "warning",
    "updated_at": "2026-11-02T06:20:00Z",
    "beds": { "code": "BED-03", "ward_id": 1, "patients": { "display_name": "이○○" } }
  }
]
```
- 경과 시간은 화면에서 `지금 - posture_since`로 계산한다 (DB에 저장하지 않음).

### 병상 타임라인: `posture_events`
```ts
supabase.from("posture_events")
  .select("posture, started_at, source")
  .eq("bed_id", bedId).gte("started_at", from).lte("started_at", to)
  .order("started_at");
```
- 각 구간의 종료 시각 = 다음 이벤트의 `started_at`.

### 알림 목록: `alerts`
```ts
supabase.from("alerts").select("*").is("acknowledged_at", null).order("triggered_at", { ascending: false });
```

### 보호자 화면 (v1): `guardian_links`로 연결된 환자의 `bed_status`, 오늘 `posture_events` 개수만

---

## 3. 엣지 (병상 PC → FastAPI)

### `POST /edge/posture-events`  (인증: `X-Device-Token`)
자세가 **확정**될 때 전송. 영상·이미지는 절대 보내지 않는다.
```json
{
  "posture": "left_lateral",
  "confidence": 0.87,
  "started_at": "2026-11-02T06:31:10Z",
  "keypoints": [[0.51, 0.22, 0.98], [0.49, 0.25, 0.95]]   // [x, y, visibility] 정규화 좌표, 선택
}
// 응답 201
{ "event_id": 981 }
```
- 서버 처리: `posture_events` 저장 → `bed_status.current_posture`, `posture_since` 갱신 → 열린 알림이 있으면 자동 해제 여부 판단.

### `POST /edge/heartbeat`  (1분마다)
```json
{ "current_posture": "left_lateral", "confidence": 0.85, "fps": 5.0 }
// 응답 200
{ "ok": true }
```
- `EDGE_OFFLINE_SEC`(기본 180초) 동안 heartbeat가 없으면 `bed_status.status = offline`.

### `POST /edge-devices`  (`admin`만)
병상 PC용 기기 토큰 발급. 토큰은 **이 응답에서 한 번만** 보여주고 DB엔 해시만 저장한다.
```json
// 요청
{ "bed_id": 3 }
// 응답 201
{ "device_id": 7, "bed_id": 3, "token": "pc_dev_..." }
```

### `DELETE /edge-devices/{device_id}`  (`admin`만) → 토큰 폐기

---

## 4. 자세 기록 (FastAPI)

### `POST /beds/{bed_id}/postures/manual` → 간호사 수동 기록/보정
```json
{ "posture": "right_lateral", "started_at": "2026-11-02T06:00:00Z", "note": "체위변경 완료" }
```
- `source = manual`, `created_by` = 요청한 사용자로 저장하고 `bed_status`를 갱신한다.

### `GET /beds/{bed_id}/postures/export?date=2026-11-02&format=csv` → 기록 내보내기 (v1)

---

## 5. 알림 (FastAPI)

### `POST /alerts/{alert_id}/ack` → 알림 확인
```json
// 응답 200
{ "id": 55, "acknowledged_by": "6f1c...", "acknowledged_at": "2026-11-02T06:42:10Z" }
```

### `POST /push/subscriptions` → 웹 푸시 구독 등록
```json
{ "endpoint": "https://...", "keys": { "p256dh": "...", "auth": "..." } }
```

### 서버 내부 동작 (API 아님)
- 알림 판단 루프: `ALERT_CHECK_SEC`(기본 3초)마다 경과 시간 확인 → `alerts` 생성, `bed_status.status` 변경.
- critical 생성 시 웹 푸시 발송.
- `ALERT_ESCALATE_MIN`(기본 5분) 동안 미확인이면 문자 발송 후 `alerts.escalated_at` 기록 (D-012).

---

## 6. 압박 히트맵 (FastAPI)

### `GET /beds/{bed_id}/pressure?window_hours=24`
부위별 누적 압박 시간. 3D 뷰어가 0~1 강도로 색칠한다.
```json
{
  "window_hours": 24,
  "regions": {
    "occiput": { "seconds": 30240, "intensity": 0.70 },
    "sacrum": { "seconds": 36000, "intensity": 0.83 },
    "heel_left": { "seconds": 30240, "intensity": 0.70 },
    "shoulder_left": { "seconds": 7200, "intensity": 0.17 }
  },
  "disclaimer": "자세 유지 시간 기반 추정이며 실제 압력 측정값이 아닙니다."
}
```
부위 키: `occiput`, `ear_left/right`, `scapula`, `shoulder_left/right`, `elbow_left/right`, `sacrum`, `ischium`, `trochanter_left/right`, `knee_left/right`, `ankle_left/right`, `heel_left/right`

---

## 7. 실시간 (Supabase Realtime)

대상 테이블 `bed_status`, `alerts`는 Supabase의 Realtime publication에 추가한다. RLS가 적용되어 각자 볼 수 있는 행의 변경만 받는다.

```ts
supabase.channel("ward-1")
  .on("postgres_changes", { event: "*", schema: "public", table: "bed_status" }, (p) => updateBed(p.new))
  .on("postgres_changes", { event: "INSERT", schema: "public", table: "alerts" }, (p) => showAlert(p.new))
  .on("postgres_changes", { event: "UPDATE", schema: "public", table: "alerts" }, (p) => markAcked(p.new))
  .subscribe();
```

| 이벤트 | 화면 동작 |
|--------|----------|
| `bed_status` UPDATE | 병상 카드 자세·색상 갱신 |
| `bed_status.status = offline` | 카드 회색 + "카메라 연결 끊김" |
| `alerts` INSERT | 알림 표시, critical이면 경고음 반복 |
| `alerts` UPDATE (`acknowledged_at` 채워짐) | 다른 화면에서도 알림 닫힘 |
