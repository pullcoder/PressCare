"""backend 호출 (T2-3). 영상·이미지는 절대 보내지 않는다 — 자세 라벨·시각·관절 좌표만. (D-002)

서버가 잠깐 꺼져 있어도 엣지는 멈추지 않는다. 보내지 못한 자세 확정 이벤트는
하나만 보관했다가 `retry_sec` 마다 다시 보낸다 (가장 최근 것이 중요하므로 덮어쓴다).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from edge.classify.stability import ConfirmedPosture

logger = logging.getLogger(__name__)


def to_iso(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, UTC).isoformat().replace("+00:00", "Z")


class BackendClient:
    def __init__(
        self,
        base_url: str,
        device_token: str,
        bed_code: str,
        timeout: float = 2.0,
        retry_sec: float = 5.0,
        http: httpx.Client | None = None,
    ) -> None:
        headers = {
            "X-Device-Token": device_token,
            # 임시: Supabase(기기 토큰 → 병상 연결) 준비 전 개발 모드에서 병상을 구분하는 값
            "X-Dev-Bed-Code": bed_code,
        }
        self._http = http or httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)
        self._http.headers.update(headers)
        self.retry_sec = retry_sec
        self._pending: dict[str, Any] | None = None
        self._next_retry = 0.0

    def _post(self, path: str, body: dict[str, Any]) -> bool:
        try:
            resp = self._http.post(path, json=body)
        except httpx.HTTPError as exc:
            logger.warning("backend 연결 실패 (%s): %s", path, exc)
            return False
        if resp.status_code >= 400:
            logger.warning("backend 오류 %s (%s): %s", resp.status_code, path, resp.text[:200])
            return False
        return True

    def send_posture_event(
        self, event: ConfirmedPosture, keypoints: list[list[float]] | None, now: float
    ) -> bool:
        body: dict[str, Any] = {
            "posture": event.posture,
            "confidence": event.confidence,
            "started_at": to_iso(event.started_at),
        }
        if keypoints is not None:
            body["keypoints"] = keypoints
        self._pending = body
        return self.retry(now, force=True)

    def retry(self, now: float, force: bool = False) -> bool:
        """보관 중인 이벤트를 다시 보낸다. 보낼 것이 없으면 True."""
        if self._pending is None:
            return True
        if not force and now < self._next_retry:
            return False
        if self._post("/edge/posture-events", self._pending):
            logger.info("자세 확정 전송: %s", self._pending["posture"])
            self._pending = None
            return True
        self._next_retry = now + self.retry_sec
        return False

    @property
    def has_pending(self) -> bool:
        return self._pending is not None

    def send_heartbeat(self, posture: str, confidence: float, fps: float) -> bool:
        return self._post(
            "/edge/heartbeat",
            {"current_posture": posture, "confidence": round(confidence, 3), "fps": round(fps, 1)},
        )

    def close(self) -> None:
        self._http.close()
