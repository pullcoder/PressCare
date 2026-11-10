"""환경변수 설정.

저장소 루트의 `.env` 하나에서 읽는다 (`.env.example`을 복사해 만든다).
기준 시간·임계값은 코드에 하드코딩하지 않고 여기서만 읽는다. (AGENTS.md 4-6)
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → 저장소 루트
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # Supabase (D-009). service role(secret) 키는 backend에서만 쓴다.
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # 체위변경 기준 (D-007)
    reposition_interval_min: int = 120
    reposition_warning_min: int = 100
    demo_time_scale: float = 1.0

    # 엣지 (병상 PC)
    edge_offline_sec: int = 180  # 이 시간 동안 heartbeat 가 없으면 offline
    edge_device_token: str = ""  # 개발 모드 임시: 엣지와 같은 .env 값. 비어 있으면 검사 안 함
    dev_memory_store: bool = False  # 개발 모드에서 Supabase 키가 있어도 임시 메모리 저장소 사용
    dev_fake_beds: int = (
        0  # 시연용 가짜 병상 수 (0~5). 카메라 병상(301-1) 옆을 채워 6인실처럼 보이게 함
    )

    # 알림 (D-012)
    alert_check_sec: float = 3.0  # 알림 판단 루프 주기 (초)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def use_memory_store(self) -> bool:
        """Supabase 준비 전(T0-3) 개발용 임시 메모리 저장소를 쓸지. production 에서는 절대 안 씀."""
        return self.app_env == "development" and (
            self.dev_memory_store or not self.supabase_configured
        )

    @property
    def time_scale(self) -> float:
        # DEMO_TIME_SCALE 은 시연 전용이므로 production 에서는 항상 1 (AGENTS.md 4-6)
        return 1.0 if self.app_env == "production" else self.demo_time_scale


@lru_cache
def get_settings() -> Settings:
    return Settings()
