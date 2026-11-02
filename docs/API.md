# API — REST · WebSocket 명세

- Base URL: `/api/v1`
- 형식: JSON, 시각은 ISO 8601 UTC (`2026-11-02T06:30:00Z`)
- 인증: 사용자 → `Authorization: Bearer <JWT>`, 엣지 기기 → `X-Device-Token: <토큰>`
- 실제 동작 명세는 서버 실행 후 `http://localhost:8000/docs`(Swagger)가 기준. **API를 바꾸면 이 문서도 같이 고친다.**

## 공통 에러 형식

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

---

## 1. 인증

### `POST /auth/login`
```json
// 요청
{ "email": "nurse@example.com", "password": "..." }
// 응답 200
{ "access_token": "eyJ...", "token_type": "bearer", "user": { "id": 1, "name": "김간호", "role": "nurse" } }
```

### `GET /auth/me` → 현재 사용자

---

## 2. 병동 · 병상 · 환자

### `GET /wards` → 병동 목록
### `GET /wards/{ward_id}/beds` → 병상 현재 상태 목록 (대시보드용)
```json
[
  {
    "bed_id": 3,
    "code": "BED-03",
    "patient": { "id": 12, "display_name": "이○○" },
    "current_posture": "supine",
    "posture_since": "2026-11-02T04:40:00Z",
    "elapsed_min": 112,
    "status": "warning",          // ok | warning | critical | unknown | offline
    "device_online": true
  }
]
```

### `POST /beds/{bed_id}/patient` → 병상에 환자 배정
```json
{ "patient_id": 12 }
```

### `POST /patients` / `GET /patients/{id}` / `PATCH /patients/{id}`
```json
{ "display_name": "이○○", "reposition_interval_min": 90 }   // null이면 기본값(120) 사용
```

---

## 3. 엣지 (병상 PC → 서버)

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

### `POST /edge/heartbeat`  (1분마다)
```json
{ "current_posture": "left_lateral", "confidence": 0.85, "fps": 5.0 }
// 응답 200
{ "ok": true }
```
- 3분 이상 heartbeat가 없으면 병상 상태 `offline`.

---

## 4. 자세 이력

### `GET /beds/{bed_id}/postures?from=...&to=...` → 타임라인
```json
[
  { "posture": "supine", "started_at": "2026-11-02T02:00:00Z", "ended_at": "2026-11-02T03:55:00Z", "duration_min": 115, "source": "edge" }
]
```

### `POST /beds/{bed_id}/postures/manual` → 간호사 수동 기록/보정
```json
{ "posture": "right_lateral", "started_at": "2026-11-02T06:00:00Z", "note": "체위변경 완료" }
```

### `GET /beds/{bed_id}/postures/export?date=2026-11-02&format=csv` → 기록 내보내기 (v1)

---

## 5. 알림

### `GET /alerts?ward_id=1&status=open` → 알림 목록
```json
[
  { "id": 55, "bed_id": 3, "level": "critical", "triggered_at": "2026-11-02T06:40:00Z", "acknowledged_at": null }
]
```

### `POST /alerts/{alert_id}/ack` → 알림 확인
```json
// 응답 200
{ "id": 55, "acknowledged_by": 1, "acknowledged_at": "2026-11-02T06:42:10Z" }
```

### `POST /push/subscriptions` → 웹 푸시 구독 등록
```json
{ "endpoint": "https://...", "keys": { "p256dh": "...", "auth": "..." } }
```

---

## 6. 압박 히트맵

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

## 7. WebSocket

### `WS /ws?token=<JWT>&ward_id=1`
서버 → 클라이언트 메시지:
```json
{ "type": "bed.status", "data": { "bed_id": 3, "current_posture": "supine", "elapsed_min": 101, "status": "warning" } }
{ "type": "alert.created", "data": { "id": 55, "bed_id": 3, "level": "critical" } }
{ "type": "alert.acknowledged", "data": { "id": 55, "acknowledged_by": 1 } }
{ "type": "device.offline", "data": { "bed_id": 3 } }
```
