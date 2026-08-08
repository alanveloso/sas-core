"""C1: BPR fail-closed when reference_models / RF backend unavailable."""

from __future__ import annotations

import builtins
import sys
from types import ModuleType
from typing import Any

import pytest

from services.border_protection import (
    BorderPfdOutcome,
    BorderProtectionUnavailable,
    evaluate_canadian_border_pfd,
    violates_canadian_border_pfd,
)


_INSTALL = {
    "latitude": 45.0,
    "longitude": -73.5,
    "height": 10.0,
    "heightType": "AGL",
    "indoorDeployment": False,
    "antennaGain": 0.0,
}
_LOW = 3_655_000_000
_HIGH = 3_670_000_000


def test_outside_arrangement_r_allows_without_models():
    outcome = evaluate_canadian_border_pfd(
        _INSTALL, max_eirp=30.0, low_hz=3_550_000_000, high_hz=3_560_000_000
    )
    assert outcome is BorderPfdOutcome.ALLOW
    assert violates_canadian_border_pfd(
        _INSTALL, 30.0, 3_550_000_000, 3_560_000_000
    ) is False


def test_missing_reference_models_is_unavailable_fail_closed(monkeypatch):
    """ImportError for reference_models must not authorize Arrangement R grants."""
    real_import = builtins.__import__

    def _block_reference_models(name, *args, **kwargs):
        if name == "reference_models" or name.startswith("reference_models."):
            raise ImportError("blocked for BPR fail-closed test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_reference_models)
    outcome = evaluate_canadian_border_pfd(
        _INSTALL, max_eirp=37.0, low_hz=_LOW, high_hz=_HIGH
    )
    assert outcome is BorderPfdOutcome.UNAVAILABLE
    assert violates_canadian_border_pfd(_INSTALL, 37.0, _LOW, _HIGH) is True


def test_missing_installation_coords_fail_closed_in_arrangement_r():
    outcome = evaluate_canadian_border_pfd(
        {"height": 6.0}, max_eirp=20.0, low_hz=_LOW, high_hz=_HIGH
    )
    assert outcome is BorderPfdOutcome.UNAVAILABLE
    assert violates_canadian_border_pfd({"height": 6.0}, 20.0, _LOW, _HIGH) is True


def test_zone_check_exception_is_unavailable(monkeypatch):
    geo = ModuleType("reference_models.geo")
    utils = ModuleType("reference_models.geo.utils")

    def _boom(*_a, **_k):
        raise RuntimeError("dataset missing")

    utils.CheckCbsdInBorderSharingZone = _boom  # type: ignore[attr-defined]
    antenna_mod = ModuleType("reference_models.antenna")
    antenna = ModuleType("reference_models.antenna.antenna")
    antenna.GetStandardAntennaGains = lambda *a, **k: 0.0  # type: ignore[attr-defined]
    antenna_mod.antenna = antenna  # type: ignore[attr-defined]
    geo.utils = utils  # type: ignore[attr-defined]

    root = ModuleType("reference_models")
    root.geo = geo  # type: ignore[attr-defined]
    root.antenna = antenna_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "reference_models", root)
    monkeypatch.setitem(sys.modules, "reference_models.geo", geo)
    monkeypatch.setitem(sys.modules, "reference_models.geo.utils", utils)
    monkeypatch.setitem(sys.modules, "reference_models.antenna", antenna_mod)
    monkeypatch.setitem(sys.modules, "reference_models.antenna.antenna", antenna)

    with pytest.raises(BorderProtectionUnavailable):
        evaluate_canadian_border_pfd(_INSTALL, 30.0, _LOW, _HIGH)
    assert violates_canadian_border_pfd(_INSTALL, 30.0, _LOW, _HIGH) is True


def test_outside_sharing_zone_allows(monkeypatch):
    geo = ModuleType("reference_models.geo")
    utils = ModuleType("reference_models.geo.utils")
    utils.CheckCbsdInBorderSharingZone = lambda *a, **k: (False, None, None)  # type: ignore[attr-defined]
    antenna_mod = ModuleType("reference_models.antenna")
    antenna = ModuleType("reference_models.antenna.antenna")
    antenna_mod.antenna = antenna  # type: ignore[attr-defined]
    geo.utils = utils  # type: ignore[attr-defined]
    root = ModuleType("reference_models")
    root.geo = geo  # type: ignore[attr-defined]
    root.antenna = antenna_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "reference_models", root)
    monkeypatch.setitem(sys.modules, "reference_models.geo", geo)
    monkeypatch.setitem(sys.modules, "reference_models.geo.utils", utils)
    monkeypatch.setitem(sys.modules, "reference_models.antenna", antenna_mod)
    monkeypatch.setitem(sys.modules, "reference_models.antenna.antenna", antenna)

    outcome = evaluate_canadian_border_pfd(_INSTALL, 40.0, _LOW, _HIGH)
    assert outcome is BorderPfdOutcome.ALLOW
    assert violates_canadian_border_pfd(_INSTALL, 40.0, _LOW, _HIGH) is False


def test_explicit_free_space_profile_computes_pfd(monkeypatch):
    """free_space is allowed only when explicitly selected — never silent ITM sub."""

    class _Angles:
        hor_cbsd = 0.0

    class _Prop:
        db_loss = 80.0
        incidence_angles = _Angles()

    geo = ModuleType("reference_models.geo")
    utils = ModuleType("reference_models.geo.utils")
    utils.CheckCbsdInBorderSharingZone = (  # type: ignore[attr-defined]
        lambda *a, **k: (True, 45.1, -73.4)
    )
    antenna_mod = ModuleType("reference_models.antenna")
    antenna = ModuleType("reference_models.antenna.antenna")
    antenna.GetStandardAntennaGains = lambda *a, **k: 0.0  # type: ignore[attr-defined]
    antenna_mod.antenna = antenna  # type: ignore[attr-defined]
    prop_pkg = ModuleType("reference_models.propagation")
    wf_itm = ModuleType("reference_models.propagation.wf_itm")
    wf_itm.CalcItmPropagationLoss = lambda *a, **k: (_ for _ in ()).throw(  # type: ignore[attr-defined]
        AssertionError("ITM must not run for free_space profile")
    )
    prop_pkg.wf_itm = wf_itm  # type: ignore[attr-defined]
    geo.utils = utils  # type: ignore[attr-defined]
    root = ModuleType("reference_models")
    root.geo = geo  # type: ignore[attr-defined]
    root.antenna = antenna_mod  # type: ignore[attr-defined]
    root.propagation = prop_pkg  # type: ignore[attr-defined]
    for name, mod in (
        ("reference_models", root),
        ("reference_models.geo", geo),
        ("reference_models.geo.utils", utils),
        ("reference_models.antenna", antenna_mod),
        ("reference_models.antenna.antenna", antenna),
        ("reference_models.propagation", prop_pkg),
        ("reference_models.propagation.wf_itm", wf_itm),
    ):
        monkeypatch.setitem(sys.modules, name, mod)

    # High EIRP + modest FS loss → deny.
    deny = evaluate_canadian_border_pfd(
        _INSTALL,
        max_eirp=50.0,
        low_hz=_LOW,
        high_hz=_HIGH,
        path_loss_model="free_space",
    )
    assert deny is BorderPfdOutcome.DENY

    allow = evaluate_canadian_border_pfd(
        _INSTALL,
        max_eirp=-40.0,
        low_hz=_LOW,
        high_hz=_HIGH,
        path_loss_model="free_space",
    )
    assert allow is BorderPfdOutcome.ALLOW


def test_itm_failure_inside_zone_denies(monkeypatch):
    geo = ModuleType("reference_models.geo")
    utils = ModuleType("reference_models.geo.utils")
    utils.CheckCbsdInBorderSharingZone = (  # type: ignore[attr-defined]
        lambda *a, **k: (True, 45.1, -73.4)
    )
    antenna_mod = ModuleType("reference_models.antenna")
    antenna = ModuleType("reference_models.antenna.antenna")
    antenna.GetStandardAntennaGains = lambda *a, **k: 0.0  # type: ignore[attr-defined]
    antenna_mod.antenna = antenna  # type: ignore[attr-defined]
    prop_pkg = ModuleType("reference_models.propagation")
    wf_itm = ModuleType("reference_models.propagation.wf_itm")

    def _itm_fail(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("NED tile missing")

    wf_itm.CalcItmPropagationLoss = _itm_fail  # type: ignore[attr-defined]
    prop_pkg.wf_itm = wf_itm  # type: ignore[attr-defined]
    geo.utils = utils  # type: ignore[attr-defined]
    root = ModuleType("reference_models")
    root.geo = geo  # type: ignore[attr-defined]
    root.antenna = antenna_mod  # type: ignore[attr-defined]
    root.propagation = prop_pkg  # type: ignore[attr-defined]
    for name, mod in (
        ("reference_models", root),
        ("reference_models.geo", geo),
        ("reference_models.geo.utils", utils),
        ("reference_models.antenna", antenna_mod),
        ("reference_models.antenna.antenna", antenna),
        ("reference_models.propagation", prop_pkg),
        ("reference_models.propagation.wf_itm", wf_itm),
    ):
        monkeypatch.setitem(sys.modules, name, mod)

    assert (
        evaluate_canadian_border_pfd(
            _INSTALL, 30.0, _LOW, _HIGH, path_loss_model="itm"
        )
        is BorderPfdOutcome.DENY
    )
