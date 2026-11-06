"""PressCare 백엔드 진입점 (T0-4 뼈대).

실행: backend/ 폴더에서 `uvicorn app.main:app --reload` → http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import dev, edge, health
from app.core.config import get_settings
from app.core.errors import register_error_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()

app = FastAPI(title="PressCare API", version="0.1.0")

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

if settings.use_memory_store:
    logging.getLogger("app").warning(
        "Supabase 설정 전: 병상 상태를 임시 메모리에 저장합니다 (서버를 끄면 사라짐)."
    )
