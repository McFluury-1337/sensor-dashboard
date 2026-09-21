from state import classify_metric, classify_reading

THRESHOLDS = {
    "temperature": (74, 83),
    "pressure": (5.4, 6.2),
    "vibration": (0.7, 1.2),
}


def test_classify_metric_temperature_normal():
    assert classify_metric(70, 74, 83) == "норма"


def test_classify_metric_temperature_warning():
    assert classify_metric(80, 74, 83) == "предупреждение"


def test_classify_metric_temperature_fault():
    assert classify_metric(95, 74, 83) == "неисправность"


def test_classify_metric_pressure_all_states():
    assert classify_metric(5.0, 5.4, 6.2) == "норма"
    assert classify_metric(5.8, 5.4, 6.2) == "предупреждение"
    assert classify_metric(7.0, 5.4, 6.2) == "неисправность"


def test_classify_metric_vibration_all_states():
    assert classify_metric(0.5, 0.7, 1.2) == "норма"
    assert classify_metric(0.9, 0.7, 1.2) == "предупреждение"
    assert classify_metric(1.5, 0.7, 1.2) == "неисправность"


def test_classify_metric_boundaries_are_inclusive_upward():
    assert classify_metric(74, 74, 83) == "предупреждение"
    assert classify_metric(83, 74, 83) == "неисправность"


def test_classify_reading_all_normal():
    assert classify_reading(70, 5.0, 0.5, THRESHOLDS) == "норма"


def test_classify_reading_worst_of_three_picks_fault():
    assert classify_reading(70, 5.8, 1.5, THRESHOLDS) == "неисправность"


def test_classify_reading_worst_of_three_picks_warning():
    assert classify_reading(70, 5.0, 0.9, THRESHOLDS) == "предупреждение"
