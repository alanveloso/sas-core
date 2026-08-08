"""Production IAP interference coupling (path loss → interference mW).

Coupling signature matches ``services.iap.engine.InterferenceCoupling``:
``(grant, protection_point, channel, eirp_dbm_mhz) -> interference_mw``.

Path-loss policy (aligned with P7/C1):
* Default / Rel1Ext: ITM via ``load_reference_engines`` — never silent Free Space.
* ``free_space`` only when ``sas_iap_path_loss_model=free_space`` (lab/test).
* Missing ITM/NED/dataset → ``PropagationUnavailableError`` (caller fail-closes).
"""

from __future__ import annotations

import math
from typing import Callable, Literal

from services.iap.aggregate import dbm_to_mw
from services.iap.engine import InterferenceCoupling
from services.iap.models import FrequencyChannel, GrantRfInfo, ProtectionPoint
from services.propagation.errors import PropagationUnavailableError

IapPathLossModel = Literal["itm", "free_space"]
DEFAULT_RX_HEIGHT_M = 1.5
FREQ_MHZ_DEFAULT = 3625.0

PathLossDbFn = Callable[[GrantRfInfo, ProtectionPoint, FrequencyChannel], float]


class IapCouplingUnavailable(PropagationUnavailableError):
    """IAP entities require coupling but the RF backend cannot provide it."""


def _configured_iap_path_loss_model() -> IapPathLossModel:
    from config import get_settings

    raw = str(getattr(get_settings(), "sas_iap_path_loss_model", "itm") or "itm")
    normalized = raw.strip().lower().replace("-", "_")
    if normalized in ("free_space", "fs", "freespace"):
        return "free_space"
    return "itm"


def iap_enabled() -> bool:
    from config import get_settings

    return bool(getattr(get_settings(), "sas_iap_enabled", True))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r_earth_km * math.asin(min(1.0, math.sqrt(a)))


def free_space_path_loss_db(
    grant: GrantRfInfo,
    point: ProtectionPoint,
    *,
    freq_mhz: float = FREQ_MHZ_DEFAULT,
    rx_height_m: float = DEFAULT_RX_HEIGHT_M,
) -> float:
    """FSPL (dB) for explicit free_space IAP profile only."""
    dist_km = _haversine_km(
        grant.latitude, grant.longitude, point.latitude, point.longitude
    )
    dh_km = abs(float(grant.height_m) - float(rx_height_m)) / 1000.0
    slant_km = max(math.sqrt(dist_km**2 + dh_km**2), 1e-6)
    return float(20.0 * math.log10(slant_km) + 20.0 * math.log10(freq_mhz) + 32.44)


def itm_path_loss_db(
    grant: GrantRfInfo,
    point: ProtectionPoint,
    *,
    rx_height_m: float = DEFAULT_RX_HEIGHT_M,
    freq_mhz: float = FREQ_MHZ_DEFAULT,
) -> float:
    """ITM median path loss; raises if reference engines / terrain unavailable."""
    from services.propagation.engines import load_reference_engines

    engines = load_reference_engines()
    try:
        result = engines.calc_itm(
            grant.latitude,
            grant.longitude,
            grant.height_m,
            point.latitude,
            point.longitude,
            rx_height_m,
            cbsd_indoor=grant.indoor,
            reliability=0.5,
            freq_mhz=freq_mhz,
            is_height_cbsd_amsl=not grant.height_is_agl,
        )
    except PropagationUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 — numerical / IO backends
        raise PropagationUnavailableError(f"IAP ITM path loss failed: {exc}") from exc
    return float(result.db_loss)


def make_iap_coupling(
    *,
    path_loss_db_fn: PathLossDbFn,
) -> InterferenceCoupling:
    """Build coupling: interference_mw = linear(eirp_dbm_mhz − path_loss_db)."""

    def coupling(
        grant: GrantRfInfo,
        point: ProtectionPoint,
        channel: FrequencyChannel,
        eirp_dbm_mhz: float,
    ) -> float:
        pl_db = float(path_loss_db_fn(grant, point, channel))
        return float(dbm_to_mw(float(eirp_dbm_mhz) - pl_db))

    return coupling


def make_production_iap_coupling(
    *,
    path_loss_model: IapPathLossModel | None = None,
    itm_path_loss_fn: Callable[..., float] | None = None,
    rx_height_m: float = DEFAULT_RX_HEIGHT_M,
) -> InterferenceCoupling:
    """Production coupling provider.

    Raises ``PropagationUnavailableError`` immediately when ITM is required but
    engines cannot be loaded (fail-closed at resolve time, not mid-IAP skip).
    """
    model = path_loss_model or _configured_iap_path_loss_model()
    if model == "free_space":

        def _fs(
            grant: GrantRfInfo, point: ProtectionPoint, channel: FrequencyChannel
        ) -> float:
            del channel
            return free_space_path_loss_db(grant, point, rx_height_m=rx_height_m)

        return make_iap_coupling(path_loss_db_fn=_fs)

    # ITM required — probe engines now so CPAS fails closed before running IAP.
    if itm_path_loss_fn is None:
        # Warm-load: raises if harness/ITM/NED unavailable.
        from services.propagation.engines import load_reference_engines

        load_reference_engines()

        def _itm(
            grant: GrantRfInfo, point: ProtectionPoint, channel: FrequencyChannel
        ) -> float:
            del channel
            return itm_path_loss_db(grant, point, rx_height_m=rx_height_m)

        return make_iap_coupling(path_loss_db_fn=_itm)

    def _itm_injected(
        grant: GrantRfInfo, point: ProtectionPoint, channel: FrequencyChannel
    ) -> float:
        del channel
        return float(itm_path_loss_fn(grant, point, rx_height_m=rx_height_m))

    return make_iap_coupling(path_loss_db_fn=_itm_injected)
