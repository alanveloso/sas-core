"""CBRS / WInnForum RF adapter: delegates to existing IAP/DPA engines.

Does not reimplement ITM, P.2108, or Free Space. Numbers stay in services/.
"""

from __future__ import annotations

from collections.abc import Callable

from rf.port import (
    RF_API_VERSION,
    RF_MODEL_PATH_LOSS,
    PathLossRequest,
    PathLossResult,
    RfUnavailableError,
)
from services.iap.coupling import free_space_path_loss_db, itm_path_loss_db
from services.iap.models import GrantRfInfo, ProtectedEntityKind, ProtectionPoint
from services.propagation.errors import PropagationUnavailableError
from services.propagation.rel1ext_dpa import calc_p2108_clutter_db, compose_dpa_pathloss_db

_BACKENDS = frozenset({"free_space", "itm", "rel1ext"})
ItmFn = Callable[[GrantRfInfo, ProtectionPoint, float, float], float]


def _grant_and_point(
    request: PathLossRequest,
) -> tuple[GrantRfInfo, ProtectionPoint]:
    freq = request.frequency_hz
    grant = GrantRfInfo(
        grant_id="rf-port",
        cbsd_id="rf-port",
        latitude=request.tx.latitude_deg,
        longitude=request.tx.longitude_deg,
        height_m=request.tx_height_m,
        height_is_agl=request.tx_height_is_agl,
        indoor=request.indoor,
        low_hz=freq,
        high_hz=freq + 1,
        max_eirp_dbm_mhz=0.0,
    )
    point = ProtectionPoint(
        point_id="rx",
        latitude=request.rx.latitude_deg,
        longitude=request.rx.longitude_deg,
        low_hz=freq,
        high_hz=freq + 1,
        threshold_dbm=0.0,
        entity_kind=ProtectedEntityKind.GENERIC,
    )
    return grant, point


class CbrsWinnForumRfAdapter:
    """Reference RF backend. Profile still selects mechanism id ``path_loss``, not this class name."""

    api_version = RF_API_VERSION
    model_id = RF_MODEL_PATH_LOSS

    def __init__(
        self,
        *,
        backend: str,
        itm_fn: ItmFn | None = None,
        terrain_elevation_m: Callable[[float, float], float] | None = None,
    ) -> None:
        if backend not in _BACKENDS:
            raise ValueError(f"unsupported RF backend: {backend}")
        self._backend = backend
        self._itm_fn = itm_fn
        self._terrain_elevation_m = terrain_elevation_m

    @property
    def provenance(self) -> str:
        return f"cbrs-winnforum:{self._backend}"

    def path_loss(self, request: PathLossRequest) -> PathLossResult:
        grant, point = _grant_and_point(request)
        freq_mhz = request.frequency_hz / 1_000_000.0
        try:
            loss = self._compute(grant, point, request, freq_mhz)
        except PropagationUnavailableError as exc:
            raise RfUnavailableError(str(exc)) from exc
        except ValueError as exc:
            raise RfUnavailableError(str(exc)) from exc
        return PathLossResult(
            loss_db=loss,
            model_id=self.model_id,
            provenance=self.provenance,
        )

    def _compute(
        self,
        grant: GrantRfInfo,
        point: ProtectionPoint,
        request: PathLossRequest,
        freq_mhz: float,
    ) -> float:
        if self._backend == "free_space":
            return float(
                free_space_path_loss_db(
                    grant, point, freq_mhz=freq_mhz, rx_height_m=request.rx_height_m
                )
            )
        itm = self._itm_median(grant, point, request, freq_mhz)
        if self._backend == "itm":
            return itm
        clutter = calc_p2108_clutter_db(
            request.tx.latitude_deg,
            request.tx.longitude_deg,
            request.tx_height_m,
            request.rx.latitude_deg,
            request.rx.longitude_deg,
            is_height_cbsd_amsl=not request.tx_height_is_agl,
            terrain_elevation_m=self._terrain_elevation_m,
        )
        return float(compose_dpa_pathloss_db(itm, clutter))

    def _itm_median(
        self,
        grant: GrantRfInfo,
        point: ProtectionPoint,
        request: PathLossRequest,
        freq_mhz: float,
    ) -> float:
        if self._itm_fn is not None:
            return float(self._itm_fn(grant, point, request.rx_height_m, freq_mhz))
        try:
            return float(
                itm_path_loss_db(
                    grant,
                    point,
                    rx_height_m=request.rx_height_m,
                    freq_mhz=freq_mhz,
                )
            )
        except PropagationUnavailableError:
            raise
        except Exception as exc:
            raise RfUnavailableError(f"itm backend unavailable: {exc}") from exc


def free_space_rf_adapter() -> CbrsWinnForumRfAdapter:
    """Zero-arg factory for entry points (lab/test Free Space only)."""
    return CbrsWinnForumRfAdapter(backend="free_space")
