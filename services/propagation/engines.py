"""Load WInnForum reference-model engines from the sibling harness checkout."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from services.propagation.errors import PropagationUnavailableError
from services.propagation.service import (
    ACTIVITY_LOSS_FACTOR_DEFAULT,
    PropagationEngines,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_harness_dir(explicit: Path | str | None = None) -> Path | None:
    if explicit is not None:
        path = Path(explicit)
        return path if path.is_dir() else None
    env = os.environ.get("SAS_HARNESS_DIR") or os.environ.get("WINNFORUM_HARNESS_DIR")
    if env:
        path = Path(env).expanduser()
        if path.is_dir():
            return path
    sibling = _REPO_ROOT.parent / "winnforum-sas-harness" / "src" / "harness"
    if sibling.is_dir():
        return sibling
    return None


def _ensure_harness_on_path(harness_dir: Path) -> None:
    resolved = str(harness_dir.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def load_reference_engines(
    harness_dir: str | None = None,
    terrain_dir: str | None = None,
    nlcd_dir: str | None = None,
) -> PropagationEngines:
    """Import harness reference models and configure terrain/NLCD drivers.

    Cache key includes harness, terrain and NLCD paths so env changes are not
    silently ignored after the first load.
    """
    root = resolve_harness_dir(harness_dir)
    if root is None:
        raise PropagationUnavailableError(
            "WInnForum harness reference_models not found "
            "(set SAS_HARNESS_DIR or place sibling winnforum-sas-harness)"
        )
    ned = Path(
        terrain_dir
        or os.environ.get("SAS_TERRAIN_DIR")
        or (_REPO_ROOT / "data" / "geo" / "ned")
    )
    nlcd = nlcd_dir if nlcd_dir is not None else os.environ.get("SAS_NLCD_DIR")
    return _load_reference_engines_cached(
        str(root.resolve()),
        str(ned.resolve()),
        (nlcd or "").strip(),
    )


@lru_cache(maxsize=8)
def _load_reference_engines_cached(
    harness_dir: str,
    terrain_dir: str,
    nlcd_dir: str,
) -> PropagationEngines:
    root = Path(harness_dir)
    _ensure_harness_on_path(root)

    try:
        from reference_models.antenna import antenna
        from reference_models.geo import drive, utils as geoutils
        from reference_models.propagation import p2108, wf_hybrid, wf_itm
    except Exception as exc:  # noqa: BLE001
        raise PropagationUnavailableError(
            f"reference_models import failed: {exc}"
        ) from exc

    try:
        drive.ConfigureTerrainDriver(terrain_dir=terrain_dir, cache_size=8)
    except Exception as exc:  # noqa: BLE001
        raise PropagationUnavailableError(
            f"terrain driver configure failed: {exc}"
        ) from exc

    if nlcd_dir:
        try:
            drive.ConfigureNlcdDriver(nlcd_dir=nlcd_dir)
        except Exception as exc:  # noqa: BLE001
            raise PropagationUnavailableError(
                f"nlcd driver configure failed: {exc}"
            ) from exc

    activity = float(getattr(p2108, "ACTIVITY_LOSS_FACTOR", ACTIVITY_LOSS_FACTOR_DEFAULT))

    def terrain_elevation_m(lat: float, lon: float) -> float:
        return float(drive.terrain_driver.GetTerrainElevation(lat, lon))

    return PropagationEngines(
        calc_itm=wf_itm.CalcItmPropagationLoss,
        calc_hybrid=wf_hybrid.CalcHybridPropagationLoss,
        calc_p2108=p2108.calc_P2108,
        activity_loss_factor=activity,
        antenna_standard_gains=antenna.GetStandardAntennaGains,
        antenna_fss_gains=antenna.GetFssAntennaGains,
        antenna_pattern_gains=antenna.GetAntennaPatternGains,
        grid_polygon=geoutils.GridPolygon,
        region_nlcd_vote=drive.nlcd_driver.RegionNlcdVote,
        terrain_elevation_m=terrain_elevation_m,
    )


def clear_reference_engines_cache() -> None:
    _load_reference_engines_cached.cache_clear()
