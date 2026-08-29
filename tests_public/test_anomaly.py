from student_api import detect_metric


def test_large_volume_drop_is_anomaly():
    history = [1000, 1010, 995, 1008, 1004, 1012, 998]
    result = detect_metric(300, history, method="zscore")
    assert result["is_anomaly"] is True


def test_stable_value_is_not_anomaly():
    history = [1000, 1010, 995, 1008, 1004, 1012, 998]
    result = detect_metric(1002, history, method="zscore")
    assert result["is_anomaly"] is False


def test_mad_anomaly_detection_with_zero_mad():
    # History with identical values
    history = [100, 100, 100, 100, 100, 100]
    res_normal = detect_metric(100, history, method="mad")
    assert res_normal["is_anomaly"] is False

    res_anom = detect_metric(200, history, method="mad")
    assert res_anom["is_anomaly"] is True


def test_auto_detector_uses_segment_context():
    # Weekend natural low volume vs weekday high volume
    weekday_history = [1000, 1020, 990, 1010, 1005]
    saturday_history = [300, 310, 295, 305]
    
    # On Saturday with 300 orders: should NOT be an anomaly when same_segment_history provided
    res = detect_metric(
        300,
        weekday_history,
        method="auto",
        context={"day_of_week": 5, "same_segment_history": saturday_history},
    )
    assert res["is_anomaly"] is False


def test_auto_detector_suppresses_known_event():
    history = [1000, 1010, 995, 1008, 1004]
    res = detect_metric(
        5000,
        history,
        method="auto",
        context={"known_event": "black_friday_promotion"},
    )
    assert res["is_anomaly"] is False

