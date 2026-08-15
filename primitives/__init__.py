"""Generic value objects: frequency, power, time, geography.

Seed of the primitive catalog. This package must not import adapters, ORM,
or protocol modules. Production request paths stay unchanged until a later
authorized extraction task wires these types.
"""

from primitives.constraint import Constraint, ConstraintKind
from primitives.decision import Decision, DecisionAction, is_apply_write
from primitives.frequency import FrequencyRange
from primitives.geography import GeoPoint, LinearRing, PointRadius, haversine_m
from primitives.power import PowerDbm, PowerMw, dbm_to_mw, mw_to_dbm
from primitives.profile_context import ProfileContext
from primitives.request import SpectrumRequest, TransmissionFootprint
from primitives.time import TimeInterval, UtcInstant

__all__ = [
    "Constraint",
    "ConstraintKind",
    "Decision",
    "DecisionAction",
    "FrequencyRange",
    "GeoPoint",
    "LinearRing",
    "PointRadius",
    "PowerDbm",
    "PowerMw",
    "ProfileContext",
    "SpectrumRequest",
    "TimeInterval",
    "TransmissionFootprint",
    "UtcInstant",
    "dbm_to_mw",
    "haversine_m",
    "is_apply_write",
    "mw_to_dbm",
]
