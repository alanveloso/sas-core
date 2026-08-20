"""G11-002: multi-profile regression — determinism, concurrency, TZ, datasets."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from primitives.time import TimeInterval, UtcInstant
from providers.discovery import DataProviderDiscovery
from spectrum_profiles.v2.context import profile_context_from_v2, profile_hash_v2
from spectrum_profiles.v2.doctor import run_profile_doctor
from spectrum_profiles.v2.parse import load_profile_v2

_PROFILE_IDS = (
    "cbrs_winnforum",
    "br_anatel_slp_3700",
    "eu_elsa",
    "us_tvws_15_711",
)


def test_all_campaign_profiles_load_doctor_and_isolate_hashes() -> None:
    parsed = {pid: load_profile_v2(pid) for pid in _PROFILE_IDS}
    hashes = {pid: profile_hash_v2(doc) for pid, doc in parsed.items()}
    assert len(set(hashes.values())) == len(_PROFILE_IDS)
    for pid, doc in parsed.items():
        assert doc.metadata.id == pid
        report = run_profile_doctor(profile_id=pid, check_plugins=False)
        assert report.ok, (pid, [f for f in report.findings if not f.ok])
        ctx = profile_context_from_v2(doc)
        assert ctx.profile_id == pid
        assert ctx.profile_hash == hashes[pid]


def test_profile_hash_deterministic_across_repeated_loads() -> None:
    for pid in _PROFILE_IDS:
        first = profile_hash_v2(load_profile_v2(pid))
        again = [profile_hash_v2(load_profile_v2(pid)) for _ in range(5)]
        assert set(again) == {first}


def test_profile_hash_invariant_under_process_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TZ", "UTC")
    if hasattr(time, "tzset"):
        time.tzset()
    baseline = {pid: profile_hash_v2(load_profile_v2(pid)) for pid in _PROFILE_IDS}

    monkeypatch.setenv("TZ", "America/Sao_Paulo")
    if hasattr(time, "tzset"):
        time.tzset()
    shifted = {pid: profile_hash_v2(load_profile_v2(pid)) for pid in _PROFILE_IDS}
    assert shifted == baseline

    monkeypatch.setenv("TZ", "Asia/Tokyo")
    if hasattr(time, "tzset"):
        time.tzset()
    again = {pid: profile_hash_v2(load_profile_v2(pid)) for pid in _PROFILE_IDS}
    assert again == baseline


def test_concurrent_multi_profile_loads_preserve_hashes() -> None:
    expected = {pid: profile_hash_v2(load_profile_v2(pid)) for pid in _PROFILE_IDS}

    def _one(pid: str) -> tuple[str, str, str]:
        doc = load_profile_v2(pid)
        return pid, doc.metadata.id, profile_hash_v2(doc)

    jobs = list(_PROFILE_IDS) * 8
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_one, pid) for pid in jobs]
        results = [fut.result() for fut in as_completed(futures)]

    assert len(results) == len(jobs)
    for pid, meta_id, digest in results:
        assert meta_id == pid
        assert digest == expected[pid]


def test_utc_instant_and_interval_timezone_normalization() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        UtcInstant(datetime(2026, 8, 20, 12, 0, 0))

    utc = datetime(2026, 8, 20, 15, 0, 0, tzinfo=timezone.utc)
    sp = utc.astimezone(ZoneInfo("America/Sao_Paulo"))
    tokyo = utc.astimezone(ZoneInfo("Asia/Tokyo"))
    assert UtcInstant(sp).value == UtcInstant(utc).value
    assert UtcInstant(tokyo).value == UtcInstant(utc).value

    start_sp = datetime(2026, 8, 20, 9, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    end_sp = start_sp + timedelta(hours=1)
    interval = TimeInterval.from_datetimes(start_sp, end_sp)
    assert interval.start.value.tzinfo == timezone.utc
    inside = UtcInstant(start_sp + timedelta(minutes=30))
    outside = UtcInstant(end_sp)
    assert interval.contains(inside) is True
    assert interval.contains(outside) is False


def test_dataset_versions_recorded_and_doctor_fail_closed_without_providers() -> None:
    # Profiles that declare data capabilities must surface them on ProfileContext.
    for pid in ("cbrs_winnforum", "br_anatel_slp_3700", "eu_elsa", "us_tvws_15_711"):
        doc = load_profile_v2(pid)
        ctx = profile_context_from_v2(doc)
        if doc.data is not None and doc.data.required_capabilities:
            assert ctx.dataset_versions
            for cap in doc.data.required_capabilities:
                assert (cap, "required") in ctx.dataset_versions
        else:
            assert ctx.dataset_versions == ()

    empty = DataProviderDiscovery(overlays={}, list_entry_points=lambda _g: ())
    report = run_profile_doctor(
        profile_id="cbrs_winnforum",
        check_plugins=True,
        require_data_plugins=True,
        data_discovery=empty,
    )
    assert report.ok is False
    assert any(not f.ok for f in report.findings)
