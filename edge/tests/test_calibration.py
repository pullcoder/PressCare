from edge.calibration import CalibrationCollector, calibration_path, load, save
from edge.classify.posture import Calibration, Measures


def test_collector_uses_median():
    c = CalibrationCollector(samples=3)
    assert c.add(Measures(0.1, 0.5, 170)) is None
    assert c.add(Measures(0.9, 0.4, None)) is None  # 튀는 값
    cal = c.add(Measures(0.2, 0.6, 172))
    assert cal == Calibration(0.2, 0.5, 171.0)


def test_save_and_load(tmp_path):
    cal = Calibration(0.05, 0.42, None)
    save("BED-01", cal, tmp_path)
    assert load("BED-01", tmp_path) == cal
    assert load("BED-02", tmp_path) is None


def test_bed_id_is_safe_file_name(tmp_path):
    assert calibration_path("../evil/1", tmp_path).parent == tmp_path


def test_broken_file_is_ignored(tmp_path):
    calibration_path("BED-01", tmp_path).write_text("{oops", encoding="utf-8")
    assert load("BED-01", tmp_path) is None
