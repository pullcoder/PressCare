from fastapi.testclient import TestClient

from app.core import supabase
from app.main import app

client = TestClient(app)


def test_health_reports_supabase_state(monkeypatch):
    for state in ("connected", "unreachable", "not_configured"):
        monkeypatch.setattr(supabase, "check_connection", lambda s=state: s)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["supabase"] == state


def test_health_never_exposes_keys(monkeypatch):
    monkeypatch.setattr(supabase, "check_connection", lambda: "connected")
    body = client.get("/api/v1/health").text
    assert "sb_secret" not in body
    assert "service_role" not in body
