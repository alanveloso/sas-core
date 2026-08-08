"""Canadian border (Arrangement R) PFD protection for Grant.

Mirrors WINNF_FT_S_BPR_testcase logic: CBSDs in the Border Sharing Zone whose
requested EIRP would produce PFD > -80 dBm/m²/MHz at the closest border point
must be rejected with responseCode 400.

Fail-closed policy:
* When Arrangement R frequency overlap applies and the required RF model /
  border geometry / dataset is unavailable, the grant is **not** authorized
  (outcome UNAVAILABLE → decision layer denies).
* Free Space path loss is used only when ``sas_bpr_path_loss_model=free_space``
  is selected explicitly; it is never a silent ITM substitute.
"""

from __future__ import annotations

import math
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Literal

# Harness reference models (ITM, Canadian border geometry, antenna gains).
_HARNESS = Path(__file__).resolve().parents[2] / "src" / "harness"
if _HARNESS.is_dir() and str(_HARNESS) not in sys.path:
    sys.path.insert(0, str(_HARNESS))

# Arrangement R: grants overlapping above 3650 MHz are subject to border PFD.
ARRANGEMENT_R_LOW_HZ = 3_650_000_000
ARRANGEMENT_R_HIGH_HZ = 3_700_000_000
PFD_LIMIT_DBM_M2_MHZ = -80.0
BORDER_RX_HEIGHT_M = 1.5
ITM_FREQ_MHZ = 3625.0

BprPathLossModel = Literal["itm", "free_space"]


class BorderPfdOutcome(str, Enum):
    """Result of Arrangement R border PFD evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    UNAVAILABLE = "unavailable"  # required model/dataset missing → fail-closed


class BorderProtectionUnavailable(Exception):
    """Required BPR reference model / dataset unavailable for a required check."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _overlaps_arrangement_r(low_hz: int, high_hz: int) -> bool:
    # Same gate as BPR harness: highFrequency > 3650 MHz.
    return high_hz > ARRANGEMENT_R_LOW_HZ and low_hz < ARRANGEMENT_R_HIGH_HZ


def _configured_bpr_path_loss_model() -> BprPathLossModel:
    from config import get_settings

    raw = str(getattr(get_settings(), "sas_bpr_path_loss_model", "itm") or "itm")
    normalized = raw.strip().lower()
    if normalized in ("free_space", "fs", "freespace"):
        return "free_space"
    return "itm"


def _free_space_path_loss_db(
    lat_tx: float,
    lon_tx: float,
    height_tx_m: float,
    lat_rx: float,
    lon_rx: float,
    height_rx_m: float,
    *,
    freq_mhz: float = ITM_FREQ_MHZ,
) -> float:
    """FSPL (dB) for explicit free_space BPR profile only."""
    # Vincenty-free haversine distance (km).
    r_earth_km = 6371.0
    phi1, phi2 = math.radians(lat_tx), math.radians(lat_rx)
    d_phi = math.radians(lat_rx - lat_tx)
    d_lambda = math.radians(lon_rx - lon_tx)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    dist_km = 2 * r_earth_km * math.asin(min(1.0, math.sqrt(a)))
    # Slant range with heights (m → km).
    dh_km = abs(height_tx_m - height_rx_m) / 1000.0
    slant_km = max(math.sqrt(dist_km**2 + dh_km**2), 1e-6)
    return float(20.0 * math.log10(slant_km) + 20.0 * math.log10(freq_mhz) + 32.44)


def evaluate_canadian_border_pfd(
    installation: dict[str, Any],
    max_eirp: float,
    low_hz: int,
    high_hz: int,
    *,
    path_loss_model: BprPathLossModel | None = None,
) -> BorderPfdOutcome:
    """Evaluate Arrangement R border PFD without authorizing on model failure."""
    if not _overlaps_arrangement_r(low_hz, high_hz):
        return BorderPfdOutcome.ALLOW

    try:
        lat = float(installation["latitude"])
        lon = float(installation["longitude"])
    except (KeyError, TypeError, ValueError):
        # Cannot prove compliance inside Arrangement R band.
        return BorderPfdOutcome.UNAVAILABLE

    ant_azi = installation.get("antennaAzimuth")
    ant_bw = installation.get("antennaBeamwidth")
    try:
        max_ant_gain = float(installation.get("antennaGain") or 0)
    except (TypeError, ValueError):
        max_ant_gain = 0.0

    model = path_loss_model or _configured_bpr_path_loss_model()

    try:
        from reference_models.antenna import antenna
        from reference_models.geo import utils
    except ImportError:
        return BorderPfdOutcome.UNAVAILABLE

    try:
        in_zone, border_lat, border_lon = utils.CheckCbsdInBorderSharingZone(
            lat, lon, ant_azi, ant_bw
        )
    except Exception as exc:  # noqa: BLE001 — geometry / dataset backends
        # Indeterminate zone membership while Arrangement R applies.
        raise BorderProtectionUnavailable(
            f"border sharing zone check failed: {exc}"
        ) from exc

    if not in_zone or border_lat is None or border_lon is None:
        return BorderPfdOutcome.ALLOW

    height = float(installation.get("height") or 0)
    height_type = installation.get("heightType") or "AGL"
    indoor = bool(installation.get("indoorDeployment"))

    try:
        if model == "free_space":
            pl = _free_space_path_loss_db(
                lat,
                lon,
                height,
                float(border_lat),
                float(border_lon),
                BORDER_RX_HEIGHT_M,
            )
            # Without ITM incidence angles, use boresight / max gain bound.
            bearing = 0.0
            try:
                ant_gain = antenna.GetStandardAntennaGains(
                    bearing, ant_azi, ant_bw, max_ant_gain
                )
            except Exception:  # noqa: BLE001
                ant_gain = max_ant_gain
        else:
            from reference_models.propagation import wf_itm

            propagation = wf_itm.CalcItmPropagationLoss(
                lat,
                lon,
                height,
                border_lat,
                border_lon,
                BORDER_RX_HEIGHT_M,
                reliability=0.5,
                cbsd_indoor=indoor,
                freq_mhz=ITM_FREQ_MHZ,
                is_height_cbsd_amsl=(height_type == "AMSL"),
            )
            pl = propagation.db_loss
            bearing = propagation.incidence_angles.hor_cbsd
            ant_gain = antenna.GetStandardAntennaGains(
                bearing, ant_azi, ant_bw, max_ant_gain
            )
    except ImportError:
        return BorderPfdOutcome.UNAVAILABLE
    except BorderProtectionUnavailable:
        raise
    except Exception:
        # Missing terrain / ITM failure while inside sharing zone: deny.
        return BorderPfdOutcome.DENY

    # PFD = requested_eirp - maxAntGain + effectiveGain - PL + 32.6
    pfd = max_eirp - max_ant_gain + ant_gain - pl + 32.6
    return BorderPfdOutcome.DENY if pfd > PFD_LIMIT_DBM_M2_MHZ else BorderPfdOutcome.ALLOW


def violates_canadian_border_pfd(
    installation: dict[str, Any],
    max_eirp: float,
    low_hz: int,
    high_hz: int,
    *,
    path_loss_model: BprPathLossModel | None = None,
) -> bool:
    """Return True when the grant must be rejected (responseCode 400).

    Fail-closed: ``UNAVAILABLE`` and ``DENY`` both reject. Does not authorize
    when reference_models / required datasets are missing.
    """
    try:
        outcome = evaluate_canadian_border_pfd(
            installation,
            max_eirp,
            low_hz,
            high_hz,
            path_loss_model=path_loss_model,
        )
    except BorderProtectionUnavailable:
        return True
    return outcome in (BorderPfdOutcome.DENY, BorderPfdOutcome.UNAVAILABLE)
