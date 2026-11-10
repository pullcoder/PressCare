"""PressCare 백엔드 진입점 (T0-4 뼈대).

실행: backend/ 폴더에서 `uvicorn app.main:app --reload` → http://localhost:8000/docs
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import dev, edge, health
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.services.memory_store import store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()

logger = logging.getLogger("app")


async def _alert_loop() -> None:
    """ALERT_CHECK_SEC 마다 경과 시간을 보고 알림을 만든다 (T3-1, 임시 저장소용)."""
    while True:
        try:
            for alert in store.tick(datetime.now(UTC), settings):
                logger.info("알림 %s: %s", alert.level, alert.bed_code)
        except Exception:  # 루프가 죽으면 알림이 멈추므로 기록만 하고 계속
            logger.exception("알림 판단 실패")
        await asyncio.sleep(settings.alert_check_sec)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = None
    if settings.use_memory_store:
        logger.warning(
            "Supabase 설정 전: 병상 상태를 임시 메모리에 저장합니다 (서버를 끄면 사라짐)."
        )
        if settings.dev_fake_beds > 0:
            store.seed_fake_beds(min(settings.dev_fake_beds, 5), datetime.now(UTC), settings)
            logger.info("시연용 가짜 병상 %d개를 만들었습니다.", min(settings.dev_fake_beds, 5))
        task = asyncio.create_task(_alert_loop())
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="PressCare API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(edge.router, prefix=API_PREFIX)
if settings.app_env != "production":
    app.include_router(dev.router, prefix=API_PREFIX)  # 임시 (Supabase 준비 전)
