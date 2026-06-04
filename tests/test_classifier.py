from core.classifier import classify_numeric


def test_classify_numeric_normal():
    assert classify_numeric(12.0, 10.0, 15.0) == "normal"


def test_classify_numeric_low():
    assert classify_numeric(9.5, 10.0, 15.0) == "low"


def test_classify_numeric_high():
    assert classify_numeric(16.0, 10.0, 15.0) == "high"
