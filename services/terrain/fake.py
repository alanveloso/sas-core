"""Deterministic HAAT provider for unit tests only (not certification)."""

from __future__ import annotations

from services.terrain.exceptions import TerrainCoordinateError, TerrainDataUnavailable


class DeterministicHaatProvider:
    """Maps ``(lat, lon)`` → fixed normalized HAAT for controlled unit tests.

    Production Registration must use ``WinnForumHaatProvider`` with real NED data.
    """

    def __init__(
        self,
        *,
        norm_haat_by_location: dict[tuple[float, float], float] | None = None,
        default_norm_haat_m: float | None = None,
        ground_alt_m: float = 0.0,
        dataset_version: str = "deterministic-test-v1",
        missing_locations: set[tuple[float, float]] | None = None,
    ) -> None:
        self._norm = dict(norm_haat_by_location or {})
        self._default = default_norm_haat_m
        self._ground_alt_m = ground_alt_m
        self._dataset_version = dataset_version
        self._missing = set(missing_locations or ())

    @property
    def dataset_version(self) -> str:
        return self._dataset_version

    def compute_haat_m(
        self,
        lat: float,
        lon: float,
        height_m: float,
        *,
        height_is_agl: bool = True,
    ) -> float:
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise TerrainCoordinateError(f"invalid coordinates lat={lat} lon={lon}")
        key = (float(lat), float(lon))
        if key in self._missing:
            raise TerrainDataUnavailable(f"no terrain for {key}")
        if key in self._norm:
            norm = self._norm[key]
        elif self._default is not None:
            norm = self._default
        else:
            raise TerrainDataUnavailable(f"no deterministic HAAT for {key}")
        if height_is_agl:
            return float(height_m) + norm
        return float(height_m) - self._ground_alt_m + norm
