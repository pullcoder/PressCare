from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app_env: str
    supabase: Literal["connected", "unreachable", "not_configured"]
