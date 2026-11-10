"""병상 기록(타임라인)·알림·시연용 가짜 병상 테스트 (임시 메모리 저장소)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.services.memory_store import MemoryBedStore, store

client = TestClient(app)
HEADERS = {"X-Device-Token": "", "X-Dev-Bed-Code": "301-1"}


@pytest.fixture(autouse=True)
def dev_settings(monkeypatch):
    s = Settings(_env_file=None, app_env="development")
    monkeypatch.setattr("app.api.v1.edge.get_settings", lambda: s)
    monkeypatch.setattr("app.api.v1.dev.get_settings", lambda: s)
    store.clear()
    yield s
    store.clear()


def post(posture, started):
    body = {"posture": posture, "confidence": 0.9, "started_at": started.isoformat()}
    return client.post("/api/v1/edge/posture-events", json=body, headers=HEADERS)


def test_timeline_lists_changes_and_totals():
    now = datetime.now(UTC)
    post("supine", now - timedelta(minutes=90))
    post("unknown", now - timedelta(minutes=70))  # 인식 불가는 기록에 안 남음
    post("left_lateral", now - timedelta(minutes=30))
    body = client.get("/api/v1/dev/beds/301-1/timeline").json()
    assert body["patient_name"] == "김○○"
    assert [e["posture"] for e in body["events"]] == ["supine", "left_lateral"]
    assert body["events"][0]["duration_min"] == pytest.approx(60, abs=0.5)
    assert body["events"][1]["ended_at"] is None
    assert body["totals_min"]["supine"] == pytest.approx(60, abs=0.5)
    assert body["reposition_count"] == 1
    assert body["longest_min"] == pytest.approx(60, abs=0.5)


def test_timeline_unknown_bed_404():
    assert client.get("/api/v1/dev/beds/NOPE/timeline").status_code == 404


def test_alerts_created_once_acked_and_resolved(dev_settings):
    now = datetime.now(UTC)
    post("supine", now - timedelta(minutes=125))
    assert [a.level for a in store.check_alerts(now, dev_settings)] == ["critical"]
    assert store.check_alerts(now, dev_settings) == []  # 같은 구간엔 한 번만

    alerts = client.get("/api/v1/dev/alerts").json()
    assert alerts[0]["bed_code"] == "301-1" and alerts[0]["acknowledged_at"] is None
    bed = client.get("/api/v1/dev/beds").json()["beds"][0]
    assert bed["alert"]["level"] == "critical"

    r = client.post(
        f"/api/v1/dev/alerts/{alerts[0]['id']}/ack", json={"acknowledged_by": "홍간호사"}
    )
    assert r.json()["acknowledged_by"] == "홍간호사"
    assert (
        client.get("/api/v1/dev/beds").json()["beds"][0]["alert"]["acknowledged_by"] == "홍간호사"
    )

    # 체위변경 기록 → 알림 자동 해제, 카드에서 사라짐
    client.post(
        "/api/v1/dev/beds/301-1/postures/manual",
        json={"posture": "left_lateral", "recorded_by": "홍간호사"},
    )
    assert client.get("/api/v1/dev/alerts").json()[0]["resolved_at"] is not None
    assert client.get("/api/v1/dev/beds").json()["beds"][0]["alert"] is None
    events = client.get("/api/v1/dev/beds/301-1/timeline").json()["events"]
    assert events[-1]["source"] == "manual" and events[-1]["recorded_by"] == "홍간호사"


def test_warning_then_critical_are_separate_alerts(dev_settings):
    now = datetime.now(UTC)
    post("supine", now - timedelta(minutes=105))
    assert [a.level for a in store.check_alerts(now, dev_settings)] == ["warning"]
    later = now + timedelta(minutes=20)
    store.heartbeat("301-1", "supine", 0.9, later)
    assert [a.level for a in store.check_alerts(later, dev_settings)] == ["critical"]


def test_ack_unknown_alert_404():
    assert client.post("/api/v1/dev/alerts/999/ack", json={}).status_code == 404


def test_fake_beds_fill_ward_and_nurse_turns_them():
    s = Settings(
        _env_file=None, demo_time_scale=60, reposition_warning_min=10, reposition_interval_min=15
    )
    st = MemoryBedStore()
    now = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    st.seed_fake_beds(5, now, s)
    beds = {b.bed_code: b for b in st.list_beds()}
    assert sorted(beds) == ["301-2", "301-3", "301-4", "301-5", "301-6"]
    assert beds["301-4"].needs_check
    assert len(st.history("301-2")) == 4  # 앞선 기록 3건 + 지금 자세

    # 시간이 충분히 흐르면 critical 알림이 생기고, 가짜 간호사가 돌려 눕혀 해제된다
    later = now + timedelta(seconds=40)  # 가속 40분
    st.tick(later, s)
    turned = st.list_beds()
    assert all(b.posture_since == later for b in turned if b.bed_code != "301-6")
    offline = next(b for b in turned if b.bed_code == "301-6")
    assert offline.last_seen < later - timedelta(seconds=s.edge_offline_sec)


def test_fake_nurse_acknowledges_critical_before_turning():
    s = Settings(
        _env_file=None, demo_time_scale=60, reposition_warning_min=10, reposition_interval_min=15
    )
    st = MemoryBedStore()
    now = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    st.seed_fake_beds(2, now, s)  # 301-3: 경과 12.75분, 간호사는 critical 뒤 5분에 옴
    st.tick(now + timedelta(seconds=3), s)  # 15.75분 → critical 알림
    st.tick(now + timedelta(seconds=5), s)  # 17.75분 → 확인됨, 아직 안 돌려 눕힘
    a = next(a for a in st.alerts() if a.bed_code == "301-3" and a.level == "critical")
    assert a.acknowledged_by == "이간호사" and a.resolved_at is None
