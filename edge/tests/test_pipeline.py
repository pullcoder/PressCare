"""엣지 처리 흐름 + backend 전송 테스트. 가짜 HTTP 서버(httpx.MockTransport)로 확인한다."""

import json

import httpx

from edge.classify.posture import PostureClassifier
from edge.classify.stability import ConfirmedPosture, StabilityFilter
from edge.client import BackendClient, to_iso
from edge.pipeline import PosturePipeline
from edge.pose.base import KP, Keypoint, PoseResult


def supine_pose() -> PoseResult:
    kps = [Keypoint(0.5, 0.5, 0.0)] * 33
    for kp, x, y in [
        (KP.NOSE, 0.5, 0.15),
        (KP.LEFT_SHOULDER, 0.6, 0.3),
        (KP.RIGHT_SHOULDER, 0.4, 0.3),
        (KP.LEFT_HIP, 0.58, 0.6),
        (KP.RIGHT_HIP, 0.42, 0.6),
    ]:
        kps[kp] = Keypoint(x, y, 0.9)
    return PoseResult(tuple(kps))


class FakeServer:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.requests: list[tuple[str, dict, httpx.Headers]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.fail:
            raise httpx.ConnectError("down")
        self.requests.append((request.url.path, json.loads(request.content), request.headers))
        return httpx.Response(201, json={"event_id": 1})

    def paths(self) -> list[str]:
        return [p for p, _, _ in self.requests]


def make_client(server: FakeServer) -> BackendClient:
    http = httpx.Client(base_url="http://test/api/v1", transport=httpx.MockTransport(server))
    return BackendClient("http://test/api/v1", "tok", "BED-01", http=http)


def test_to_iso_is_utc():
    assert to_iso(0) == "1970-01-01T00:00:00Z"


def test_pipeline_sends_heartbeat_then_confirmed_posture():
    server = FakeServer()
    pipe = PosturePipeline(
        PostureClassifier(), StabilityFilter(stable_sec=5, grace_sec=1), make_client(server), 60
    )
    for t in range(7):
        pipe.process(supine_pose(), 1000.0 + t, 5.0)

    assert server.paths() == ["/api/v1/edge/heartbeat", "/api/v1/edge/posture-events"]
    _, event, headers = server.requests[1]
    assert event["posture"] == "supine"
    assert event["started_at"] == to_iso(1000.0)
    assert len(event["keypoints"]) == 33 and len(event["keypoints"][0]) == 3
    assert headers["X-Device-Token"] == "tok"
    assert headers["X-Dev-Bed-Code"] == "BED-01"


def test_no_person_becomes_absent_without_keypoints():
    server = FakeServer()
    pipe = PosturePipeline(
        PostureClassifier(), StabilityFilter(stable_sec=2, grace_sec=1), make_client(server)
    )
    for t in range(3):
        pipe.process(None, float(t), 5.0)
    _, event, _ = server.requests[-1]
    assert event["posture"] == "absent"
    assert "keypoints" not in event


def test_failed_event_is_kept_and_retried():
    server = FakeServer(fail=True)
    client = make_client(server)
    ev = ConfirmedPosture("supine", 0.0, 0.9)
    assert client.send_posture_event(ev, None, now=0.0) is False
    assert client.has_pending
    server.fail = False
    assert client.retry(now=1.0) is False  # 아직 재시도 시간이 아님
    assert client.retry(now=6.0) is True
    assert not client.has_pending
    assert server.paths() == ["/api/v1/edge/posture-events"]
