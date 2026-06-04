from core.pipeline import process_lab_report


def test_unresolved_test_is_discarded():
    """Verify that unresolved tests are discarded per Issue #1 requirement."""
    raw_text = "New Biomarker 5.2 mg/dL (2.0-6.0)\n"
    resolved_tests, tracker = process_lab_report(raw_text)

    assert len(resolved_tests) == 0
    assert tracker.dropped == 1
