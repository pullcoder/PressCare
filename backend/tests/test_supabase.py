import httpx
import pytest

from app.core import supabase
from app.core.config import Settings
from app.core.errors import AppError


def use_settings(monkeypatch, **values):
    settings = Settings(_env_file=None, **values)
    monkeypatch.setattr(supabase, "get_settings", lambda: settings)


def test_not_configured_without_keys(monkeypatch):
    use_settings(monkeypatch, supabase_url="", supabase_service_role_key="")
    assert supabase.check_connection() == "not_configured"


def test_get_client_without_keys_raises_app_error(monkeypatch):
    use_settings(monkeypatch, supabase_url="", supabase_service_role_key="")
    supabase.get_supabase.cache_clear()
    with pytest.raises(AppError) as exc:
        supabase.get_supabase()
    assert exc.value.code == "SUPABASE_NOT_CONFIGURED"


def test_connected_when_auth_health_ok(monkeypatch):
    use_settings(monkeypatch, supabase_url="https://x.supabase.co", supabase_service_role_key="k")
    monkeypatch.setattr(supabase.httpx, "get", lambda *a, **kw: httpx.Response(200))
    assert supabase.check_connection() == "connected"


def test_unreachable_on_network_error(monkeypatch):
    use_settings(monkeypatch, supabase_url="https://x.supabase.co", supabase_service_role_key="k")

    def fail(*a, **kw):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(supabase.httpx, "get", fail)
    assert supabase.check_connection() == "unreachable"
