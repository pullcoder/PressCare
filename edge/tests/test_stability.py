"""깜빡임 방지 필터 테스트 (T1-3). 1초에 1프레임씩 넣는다고 가정한다."""

import pytest

from edge.classify.stability import ConfirmedPosture, StabilityFilter


def feed(f: StabilityFilter, labels: list[str], start: float = 0.0, conf: float = 0.9):
    """labels[i] 를 시각 start+i 에 넣고, 확정 이벤트만 모아 돌려준다."""
    events = []
    for i, label in enumerate(labels):
        ev = f.update(label, conf, start + i)
        if ev is not None:
            events.append((start + i, ev))
    return events


def test_confirms_after_stable_sec_with_original_start_time():
    f = StabilityFilter(stable_sec=30)
    events = feed(f, ["supine"] * 31)
    assert events == [(30, ConfirmedPosture("supine", 0, 0.9))]
    assert f.confirmed == "supine"


def test_not_confirmed_before_stable_sec():
    f = StabilityFilter(stable_sec=30)
    assert feed(f, ["supine"] * 30) == []
    assert f.confirmed is None


def test_short_glitch_does_not_reset_timer():
    f = StabilityFilter(stable_sec=30, grace_sec=3)
    labels = ["supine"] * 10 + ["unknown"] * 2 + ["supine"] * 19
    events = feed(f, labels)
    assert [(t, e.posture, e.started_at) for t, e in events] == [(30, "supine", 0)]


def test_real_change_is_confirmed_with_change_time():
    f = StabilityFilter(stable_sec=30, grace_sec=3)
    feed(f, ["supine"] * 31)  # 0초에 시작한 앙와위 확정
    events = feed(f, ["left_lateral"] * 31, start=31)
    assert [(t, e.posture, e.started_at) for t, e in events] == [(61, "left_lateral", 31)]


def test_same_posture_is_not_confirmed_twice():
    f = StabilityFilter(stable_sec=5, grace_sec=1)
    feed(f, ["supine"] * 6)
    events = feed(f, ["unknown"] * 2 + ["supine"] * 10, start=6)
    assert events == []  # 잠깐 unknown 이었다가 같은 자세로 돌아옴 → 새 이벤트 없음


def test_absent_is_confirmed_like_other_labels():
    f = StabilityFilter(stable_sec=5, grace_sec=1)
    feed(f, ["supine"] * 6)
    events = feed(f, ["absent"] * 7, start=6)
    assert [e.posture for _, e in events] == ["absent"]


def test_flicker_between_two_labels_never_confirms_wrong_one():
    f = StabilityFilter(stable_sec=10, grace_sec=3)
    events = feed(f, ["supine", "left_lateral"] * 20)
    assert [e.posture for _, e in events] == ["supine"]  # 계속 바뀌는 라벨은 오인식으로 무시


def test_average_confidence():
    f = StabilityFilter(stable_sec=2, grace_sec=1)
    f.update("supine", 0.6, 0)
    f.update("supine", 0.8, 1)
    ev = f.update("supine", 1.0, 2)
    assert ev is not None and ev.confidence == pytest.approx(0.8)


def test_invalid_settings():
    with pytest.raises(ValueError):
        StabilityFilter(stable_sec=0)
