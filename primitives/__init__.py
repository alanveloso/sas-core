"""Generic value objects: frequency, power, time, geography.

Seed of the primitive catalog. This package must not import adapters, ORM,
or protocol modules. Production request paths stay unchanged until a later
authorized extraction task wires these types.
"""

from primitives.frequency import FrequencyRange
from primitives.geography import GeoPoint, LinearRing, PointRadius, haversine_m
from primitives.power import PowerDbm, PowerMw, dbm_to_mw, mw_to_dbm
from primitives.time import TimeInterval, UtcInstant

__all__ = [
    "FrequencyRange",
    "GeoPoint",
    "LinearRing",
    "PointRadius",
    "PowerDbm",
    "PowerMw",
    "TimeInterval",
    "UtcInstant",
    "dbm_to_mw",
    "haversine_m",
    "mw_to_dbm",
]
