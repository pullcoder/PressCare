"""엣지 수신 API + 임시 메모리 저장소 + 상태 판단 테스트."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.memory_store import store
from app.services.reposition import elapsed_minutes, evaluate_status

client = TestClient(app)
HEADERS = {"X-Device-Token": "", "X-Dev-Bed-Code": "BED-01"}
NOW = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def dev_settings(monkeypatch):
    s = Settings(_env_file=None, app_env="development")
    app.dependency_overrides.clear()
    monkeypatch.setattr("app.api.v1.edge.get_settings", lambda: s)
    monkeypatch.setattr("app.api.v1.dev.get_settings", lambda: s)
    store.clear()
    yield s
    store.clear()


def event(posture="left_lateral", started_at="2026-11-06T09:00:00Z"):
    return {"posture": posture, "confidence": 0.87, "started_at": started_at}


def test_posture_event_then_dashboard_list():
    started = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    r = client.post("/api/v1/edge/posture-events", json=event(started_at=started), headers=HEADERS)
    assert r.status_code == 201 and r.json()["event_id"] == 1
    body = client.get("/api/v1/dev/beds").json()
    assert body["time_scale"] == 1
    bed = body["beds"][0]
    assert bed["bed_code"] == "BED-01"
    assert bed["current_posture"] == "left_lateral"
    assert bed["status"] == "ok"
    assert 4.9 < bed["elapsed_min"] < 5.5


def test_heartbeat_makes_new_bed_visible():
    r = client.post(
        "/api/v1/edge/heartbeat",
        json={"current_posture": "unknown", "confidence": 0, "fps": 5},
        headers=HEADERS,
    )
    assert r.json() == {"ok": True}
    assert client.get("/api/v1/dev/beds").json()["beds"][0]["status"] == "unknown"


def test_rejects_bad_input():
    bad = [
        event(posture="prone"),
        {**event(), "confidence": 1.5},
        event(started_at="2026-11-06T09:00:00"),  # 시간대 없음
        {**event(), "keypoints": [[0.1, 0.2, 0.9]] * 10},
    ]
    for body in bad:
        assert (
            client.post("/api/v1/edge/posture-events", json=body, headers=HEADERS).status_code
            == 422
        )


def test_bed_code_header_required():
    r = client.post("/api/v1/edge/posture-events", json=event(), headers={"X-Device-Token": ""})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BED_CODE_REQUIRED"


def test_device_token_checked_when_configured(dev_settings):
    dev_settings.edge_device_token = "secret-token"
    r = client.post("/api/v1/edge/posture-events", json=event(), headers=HEADERS)
    assert r.status_code == 401
    ok = {**HEADERS, "X-Device-Token": "secret-token"}
    assert client.post("/api/v1/edge/posture-events", json=event(), headers=ok).status_code == 201


def test_memory_store_off_when_supabase_configured(dev_settings):
    dev_settings.supabase_url = "https://x.supabase.co"
    dev_settings.supabase_service_role_key = "sb_secret_x"
    assert (
        client.post("/api/v1/edge/posture-events", json=event(), headers=HEADERS).status_code == 501
    )
    assert client.get("/api/v1/dev/beds").status_code == 404


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(0, "ok"), (99, "ok"), (100, "warning"), (119, "warning"), (120, "critical")],
)
def test_status_by_elapsed_time(minutes, expected):
    s = Settings(_env_file=None)
    since = NOW - timedelta(minutes=minutes)
    assert evaluate_status("supine", since, NOW, NOW, s) == expected


def test_demo_time_scale_10s_warning_15s_critical():
    # 시연 설정: REPOSITION_WARNING_MIN=10, REPOSITION_INTERVAL_MIN=15, DEMO_TIME_SCALE=60
    s = Settings(
        _env_file=None, reposition_warning_min=10, reposition_interval_min=15, demo_time_scale=60
    )
    status = [
        evaluate_status("supine", NOW - timedelta(seconds=sec), NOW, NOW, s) for sec in (9, 10, 15)
    ]
    assert status == ["ok", "warning", "critical"]


def test_production_ignores_demo_scale():
    s = Settings(_env_file=None, app_env="production", demo_time_scale=60)
    assert evaluate_status("supine", NOW - timedelta(seconds=15), NOW, NOW, s) == "ok"
    assert elapsed_minutes(NOW - timedelta(minutes=1), NOW, s.time_scale) == 1
    assert not s.use_memory_store


def test_offline_and_unknown():
    s = Settings(_env_file=None)
    assert evaluate_status("supine", NOW, NOW - timedelta(seconds=181), NOW, s) == "offline"
    assert evaluate_status("absent", NOW, NOW, NOW, s) == "unknown"
    assert evaluate_status("unknown", NOW, NOW, NOW, s) == "unknown"


def test_get_settings_still_cached():
    assert get_settings() is get_settings()


# ----- 인식이 안 될 때 타이머 유지 (이불·어둠) -----
def post(posture, started):
    return client.post(
        "/api/v1/edge/posture-events", json=event(posture, started.isoformat()), headers=HEADERS
    )


def only_bed():
    return client.get("/api/v1/dev/beds").json()["beds"][0]


def test_unknown_keeps_last_posture_timer():
    t0 = datetime.now(UTC) - timedelta(minutes=30)
    post("left_lateral", t0)
    post("unknown", t0 + timedelta(minutes=20))
    bed = only_bed()
    assert bed["current_posture"] == "left_lateral"
    assert bed["needs_check"] is True
    assert 29.5 < bed["elapsed_min"] < 31


def test_same_posture_after_unknown_continues_timer():
    t0 = datetime.now(UTC) - timedelta(minutes=30)
    post("supine", t0)
    post("unknown", t0 + timedelta(minutes=10))
    post("supine", t0 + timedelta(minutes=20))
    bed = only_bed()
    assert bed["needs_check"] is False
    assert bed["elapsed_min"] > 29.5  # 처음 시각부터 이어짐


def test_new_posture_after_unknown_restarts_timer():
    t0 = datetime.now(UTC) - timedelta(minutes=30)
    post("supine", t0)
    post("unknown", t0 + timedelta(minutes=10))
    post("right_lateral", datetime.now(UTC))
    bed = only_bed()
    assert bed["current_posture"] == "right_lateral"
    assert bed["elapsed_min"] < 1


def test_unknown_first_is_just_unknown():
    post("unknown", datetime.now(UTC))
    bed = only_bed()
    assert bed["current_posture"] == "unknown" and bed["status"] == "unknown"


# ----- 간호사 "체위변경 완료" -----
def test_manual_reposition_resets_timer():
    post("supine", datetime.now(UTC) - timedelta(minutes=125))
    assert only_bed()["status"] == "critical"
    r = client.post("/api/v1/dev/beds/BED-01/postures/manual", json={"posture": "right_lateral"})
    assert r.json() == {"ok": True}
    bed = only_bed()
    assert bed["current_posture"] == "right_lateral"
    assert bed["status"] == "ok" and bed["source"] == "manual"


def test_manual_unknown_bed_404():
    r = client.post("/api/v1/dev/beds/NOPE/postures/manual", json={"posture": "supine"})
    assert r.status_code == 404
