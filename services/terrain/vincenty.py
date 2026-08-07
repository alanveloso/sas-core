"""Minimal Vincenty direct formula (WGS84) for HAAT radial sampling.

Algorithm matches WInnForum ``reference_models.geo.vincenty.GeodesicPoint``
(Vincenty 1975) so HAAT radials are reproducible against the official harness.
"""

from __future__ import annotations

from math import atan, atan2, cos, degrees, radians, sin, tan


def geodesic_point(
    lat: float,
    lon: float,
    dist_km: float,
    bearing_deg: float,
    *,
    accuracy: float = 1.0e-12,
) -> tuple[float, float]:
    """Return ``(lat, lon)`` at ``dist_km`` along ``bearing_deg`` from start."""
    a = 6378.1370
    f = 1.0 / 298.257223563
    b = (1 - f) * a

    phi1 = radians(lat)
    l1 = radians(lon)
    alpha1 = radians(bearing_deg)
    s = dist_km

    u1 = atan((1 - f) * tan(phi1))
    sigma1 = atan2(tan(u1), cos(alpha1))
    sin_alpha = cos(u1) * sin(alpha1)
    cos_sq_alpha = 1.0 - sin_alpha**2
    usq = cos_sq_alpha * (a**2 - b**2) / b**2

    a_coeff = 1 + usq / 16384.0 * (4096.0 + usq * (-768 + usq * (320.0 - 175.0 * usq)))
    b_coeff = usq / 1024.0 * (256.0 + usq * (-128.0 + usq * (74.0 - 47.0 * usq)))

    sigma = s / (b * a_coeff)
    last_sigma = 1.0e40
    while abs(sigma - last_sigma) > accuracy:
        last_sigma = sigma
        two_sigma_m = 2.0 * sigma1 + sigma
        d_sigma = (
            b_coeff
            * sin(sigma)
            * (
                cos(two_sigma_m)
                + 0.25
                * b_coeff
                * (
                    cos(sigma) * (-1.0 + 2.0 * cos(two_sigma_m) ** 2)
                    - (1.0 / 6.0)
                    * b_coeff
                    * cos(two_sigma_m)
                    * (-3.0 + 4.0 * sin(sigma) ** 2)
                    * (-3.0 + 4.0 * cos(two_sigma_m) ** 2)
                )
            )
        )
        sigma = s / (b * a_coeff) + d_sigma

    num = sin(u1) * cos(sigma) + cos(u1) * sin(sigma) * cos(alpha1)
    den = (1.0 - f) * (
        sin_alpha**2
        + (sin(u1) * sin(sigma) - cos(u1) * cos(sigma) * cos(alpha1)) ** 2
    ) ** 0.5
    phi2 = atan2(num, den)

    num = sin(sigma) * sin(alpha1)
    den = cos(u1) * cos(sigma) - sin(u1) * sin(sigma) * cos(alpha1)
    lmbda = atan2(num, den)

    c = (f / 16.0) * cos_sq_alpha * (4.0 + f * (4.0 - 3.0 * cos_sq_alpha))
    l2 = l1 + lmbda - (1.0 - c) * f * sin_alpha * (
        sigma
        + c
        * sin(sigma)
        * (
            cos(two_sigma_m)
            + c * cos(sigma) * (-1.0 + 2.0 * cos(two_sigma_m) ** 2)
        )
    )

    # Keep lon in (-180, 180]
    lon2 = (degrees(l2) + 180.0) % 360.0 - 180.0
    return degrees(phi2), lon2


def geodesic_points(
    lat: float,
    lon: float,
    distances_km: list[float],
    bearing_deg: float,
) -> tuple[list[float], list[float]]:
    """Vectorized wrapper: points at several distances along one bearing."""
    lats: list[float] = []
    lons: list[float] = []
    for dist in distances_km:
        plat, plon = geodesic_point(lat, lon, dist, bearing_deg)
        lats.append(plat)
        lons.append(plon)
    return lats, lons
