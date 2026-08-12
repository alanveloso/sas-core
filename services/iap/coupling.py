"""Production IAP interference coupling (path loss → interference mW).

Coupling signature matches ``services.iap.engine.InterferenceCoupling``:
``(grant, protection_point, channel, eirp_dbm_mhz) -> interference_mw``.

Path-loss policy (aligned with P7/C1):
* Default / Rel1Ext: ITM via ``load_reference_engines`` — never silent Free Space.
* ``free_space`` only when ``sas_iap_path_loss_model=free_space`` (lab/test).
* Missing ITM/NED/dataset → ``PropagationUnavailableError`` (caller fail-closes).

ESC entities use a dedicated path aligned with WInnForum
``computeInterferenceEsc`` (effective EIRP − ITM − ESC mask). Non-ESC entities
keep the generic ``eirp − path_loss`` coupling.
"""

from __future__ import annotations

import math
from typing import Callable, Literal, Sequence

from services.iap.aggregate import dbm_to_mw
from services.iap.engine import InterferenceCoupling
from services.iap.models import (
    FrequencyChannel,
    GrantRfInfo,
    ProtectedEntityKind,
    ProtectionPoint,
)
from services.propagation.errors import PropagationUnavailableError

IapPathLossModel = Literal["itm", "free_space"]
DEFAULT_RX_HEIGHT_M = 1.5
FREQ_MHZ_DEFAULT = 3625.0

# Normative ESC / WINNF interference.py constants (not fixture copies).
ESC_PASSBAND_LOW_HZ = 3_550_000_000
ESC_PASSBAND_HIGH_HZ = 3_680_000_000
ESC_MASK_EDGE_HZ = 3_650_000_000
ESC_IN_BAND_INSERTION_LOSS_DB = 0.5
ESC_RBW_HZ = 5_000_000.0
ESC_FREQ_PROP_MHZ = 3625.0
MHZ_HZ = 1_000_000.0

PathLossDbFn = Callable[[GrantRfInfo, ProtectionPoint, FrequencyChannel], float]
ItmEscResultFn = Callable[..., object]
AntennaGainFn = Callable[..., float]


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


def _linear_to_db(value: float) -> float:
    return 10.0 * math.log10(value)


def _db_to_linear(value: float) -> float:
    return 10.0 ** (value / 10.0)


def effective_system_eirp_dbm(
    max_eirp_dbm_mhz: float,
    cbsd_max_ant_gain_dbi: float,
    effective_ant_gain_dbi: float,
    *,
    reference_bandwidth_hz: float = ESC_RBW_HZ,
) -> float:
    """WINNF ``getEffectiveSystemEirp`` semantics (dBm in reference bandwidth)."""
    return (
        (float(max_eirp_dbm_mhz) - float(cbsd_max_ant_gain_dbi))
        + float(effective_ant_gain_dbi)
        + _linear_to_db(float(reference_bandwidth_hz) / MHZ_HZ)
    )


def esc_mask_loss_db(channel: FrequencyChannel) -> float:
    """WINNF ``getEscMaskLoss`` using the protection channel (not grant) edges."""
    if channel.high_hz <= ESC_MASK_EDGE_HZ:
        return ESC_IN_BAND_INSERTION_LOSS_DB
    if channel.low_hz < ESC_MASK_EDGE_HZ:
        raise IapCouplingUnavailable(
            "ESC mask loss: inconsistent protection channel crossing 3650 MHz"
        )
    # 1 MHz bins centered mid-bin from low+0.5 MHz to high (exclusive of high).
    attens: list[float] = []
    freq_hz = float(channel.low_hz) + 0.5 * MHZ_HZ
    while freq_hz < float(channel.high_hz):
        attens.append(freq_hz / MHZ_HZ - 3650.0 + ESC_IN_BAND_INSERTION_LOSS_DB)
        freq_hz += MHZ_HZ
    if not attens:
        raise IapCouplingUnavailable("ESC mask loss: empty frequency sampling")
    mean_lin = sum(_db_to_linear(-a) for a in attens) / float(len(attens))
    return float(-_linear_to_db(mean_lin))


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


def _require_esc_point_rf(point: ProtectionPoint) -> tuple[float, float, tuple[float, ...]]:
    if point.receiver_height_m is None:
        raise IapCouplingUnavailable("ESC coupling requires receiver_height_m")
    if point.receiver_antenna_azimuth_deg is None:
        raise IapCouplingUnavailable(
            "ESC coupling requires receiver_antenna_azimuth_deg"
        )
    pattern = point.receiver_antenna_gain_pattern_dbi
    if pattern is None or len(pattern) == 0:
        raise IapCouplingUnavailable(
            "ESC coupling requires receiver_antenna_gain_pattern_dbi"
        )
    return (
        float(point.receiver_height_m),
        float(point.receiver_antenna_azimuth_deg),
        tuple(float(x) for x in pattern),
    )


def _require_grant_antenna(grant: GrantRfInfo) -> tuple[float, float, float]:
    if (
        grant.antenna_azimuth_deg is None
        or grant.antenna_beamwidth_deg is None
        or grant.antenna_gain_dbi is None
    ):
        raise IapCouplingUnavailable(
            "ESC coupling requires CBSD antenna azimuth/beamwidth/gain"
        )
    return (
        float(grant.antenna_azimuth_deg),
        float(grant.antenna_beamwidth_deg),
        float(grant.antenna_gain_dbi),
    )


def _default_itm_esc_result(
    grant: GrantRfInfo,
    point: ProtectionPoint,
    *,
    rx_height_m: float,
):
    from services.propagation.engines import load_reference_engines

    engines = load_reference_engines()
    try:
        return engines.calc_itm(
            grant.latitude,
            grant.longitude,
            grant.height_m,
            point.latitude,
            point.longitude,
            rx_height_m,
            cbsd_indoor=grant.indoor,
            reliability=-1,
            freq_mhz=ESC_FREQ_PROP_MHZ,
            is_height_cbsd_amsl=not grant.height_is_agl,
        )
    except PropagationUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PropagationUnavailableError(
            f"ESC ITM path loss failed: {exc}"
        ) from exc


def _default_cbsd_antenna_gain(
    hor_cbsd: float,
    antenna_azimuth_deg: float,
    antenna_beamwidth_deg: float,
    antenna_gain_dbi: float,
) -> float:
    from services.propagation.engines import load_reference_engines

    engines = load_reference_engines()
    return float(
        engines.antenna_standard_gains(
            hor_cbsd,
            antenna_azimuth_deg,
            antenna_beamwidth_deg,
            antenna_gain_dbi,
        )
    )


def _default_esc_antenna_gain(
    hor_rx: float,
    antenna_azimuth_deg: float,
    pattern_dbi: Sequence[float],
) -> float:
    from services.propagation.engines import load_reference_engines

    engines = load_reference_engines()
    gain_fn = getattr(engines, "antenna_pattern_gains", None)
    if gain_fn is None:
        raise IapCouplingUnavailable("ESC antenna pattern gain backend unavailable")
    try:
        import numpy as np

        pattern_arg: Sequence[float] | object = np.asarray(pattern_dbi, dtype=float)
    except ImportError:
        pattern_arg = pattern_dbi
    return float(gain_fn(hor_rx, antenna_azimuth_deg, pattern_arg))


def make_esc_iap_coupling(
    *,
    itm_result_fn: ItmEscResultFn | None = None,
    cbsd_antenna_gain_fn: AntennaGainFn | None = None,
    esc_antenna_gain_fn: AntennaGainFn | None = None,
) -> InterferenceCoupling:
    """ESC coupling: effective EIRP − ITM − ESC mask → mW (WINNF semantics)."""

    itm_fn = itm_result_fn or _default_itm_esc_result
    cbsd_fn = cbsd_antenna_gain_fn or _default_cbsd_antenna_gain
    esc_fn = esc_antenna_gain_fn or _default_esc_antenna_gain

    def coupling(
        grant: GrantRfInfo,
        point: ProtectionPoint,
        channel: FrequencyChannel,
        eirp_dbm_mhz: float,
    ) -> float:
        if point.entity_kind is not ProtectedEntityKind.ESC:
            raise IapCouplingUnavailable("make_esc_iap_coupling requires ESC point")
        rx_h, esc_az, pattern = _require_esc_point_rf(point)
        cbsd_az, cbsd_bw, cbsd_peak = _require_grant_antenna(grant)

        try:
            result = itm_fn(grant, point, rx_height_m=rx_h)
        except TypeError:
            # Injected stubs may omit kwargs.
            result = itm_fn(grant, point)

        try:
            db_loss = float(result.db_loss)
            hor_cbsd = float(result.incidence_angles.hor_cbsd)
            hor_rx = float(result.incidence_angles.hor_rx)
        except (AttributeError, TypeError, ValueError) as exc:
            raise IapCouplingUnavailable(
                "ESC ITM result missing db_loss/incidence angles"
            ) from exc

        g_cbsd = float(cbsd_fn(hor_cbsd, cbsd_az, cbsd_bw, cbsd_peak))
        g_esc = float(esc_fn(hor_rx, esc_az, pattern))
        eirp_eff = effective_system_eirp_dbm(
            float(eirp_dbm_mhz), cbsd_peak, g_cbsd + g_esc
        )
        mask = esc_mask_loss_db(channel)
        interf_dbm = eirp_eff - db_loss - mask
        return float(dbm_to_mw(interf_dbm))

    return coupling


def make_production_iap_coupling(
    *,
    path_loss_model: IapPathLossModel | None = None,
    itm_path_loss_fn: Callable[..., float] | None = None,
    rx_height_m: float = DEFAULT_RX_HEIGHT_M,
) -> InterferenceCoupling:
    """Production coupling provider with ESC entity dispatch.

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

        generic = make_iap_coupling(path_loss_db_fn=_fs)
    elif itm_path_loss_fn is None:
        from services.propagation.engines import load_reference_engines

        load_reference_engines()

        def _itm(
            grant: GrantRfInfo, point: ProtectionPoint, channel: FrequencyChannel
        ) -> float:
            del channel
            return itm_path_loss_db(grant, point, rx_height_m=rx_height_m)

        generic = make_iap_coupling(path_loss_db_fn=_itm)
    else:

        def _itm_injected(
            grant: GrantRfInfo, point: ProtectionPoint, channel: FrequencyChannel
        ) -> float:
            del channel
            return float(itm_path_loss_fn(grant, point, rx_height_m=rx_height_m))

        generic = make_iap_coupling(path_loss_db_fn=_itm_injected)

    esc = make_esc_iap_coupling()

    def dispatch(
        grant: GrantRfInfo,
        point: ProtectionPoint,
        channel: FrequencyChannel,
        eirp_dbm_mhz: float,
    ) -> float:
        if point.entity_kind is ProtectedEntityKind.ESC:
            return esc(grant, point, channel, eirp_dbm_mhz)
        return generic(grant, point, channel, eirp_dbm_mhz)

    return dispatch
