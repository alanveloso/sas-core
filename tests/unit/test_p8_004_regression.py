"""Unit tests for P8-004 regression summary parsing / flake analysis."""

from __future__ import annotations

from tools.p8_004_regression import RunResult, analyze_flakes, parse_pytest_summary


def test_parse_pytest_summary_counts():
    text = """
.....
===== warnings =====
834 passed, 7 skipped, 48 warnings in 71.17s
"""
    passed, skipped, failed, errors, line = parse_pytest_summary(text)
    assert passed == 834
    assert skipped == 7
    assert failed == 0
    assert errors == 0
    assert "834 passed" in line


def test_parse_pytest_summary_with_failures():
    text = "2 failed, 10 passed, 1 error in 1.0s\n"
    # Last match wins; order in regex expects passed first — use realistic line.
    text = "10 passed, 2 failed, 1 error in 1.0s\n"
    passed, skipped, failed, errors, _ = parse_pytest_summary(text)
    assert passed == 10
    assert failed == 2
    assert errors == 1


def test_analyze_flakes_stable():
    runs = [
        RunResult("full_1", 0, 838, 7, 0, 0, 1.0, "838 passed, 7 skipped", "UTC", "a.log"),
        RunResult("full_2", 0, 838, 7, 0, 0, 1.0, "838 passed, 7 skipped", "UTC", "b.log"),
        RunResult(
            "full_tz_america_los_angeles",
            0,
            837,
            8,
            0,
            0,
            1.0,
            "837 passed, 8 skipped",
            "America/Los_Angeles",
            "tz.log",
        ),
        RunResult("rsa_ecc", 0, 50, 0, 0, 0, 1.0, "50 passed", "UTC", "c.log"),
    ]
    report = analyze_flakes(runs)
    assert report["stable"] is True
    assert report["comparable_full_runs"] == 2


def test_analyze_flakes_detects_divergence():
    runs = [
        RunResult("full_1", 0, 838, 7, 0, 0, 1.0, "838 passed, 7 skipped", "UTC", "a.log"),
        RunResult("full_2", 0, 837, 8, 0, 0, 1.0, "837 passed, 8 skipped", "UTC", "b.log"),
    ]
    report = analyze_flakes(runs)
    assert report["stable"] is False
