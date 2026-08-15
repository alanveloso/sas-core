"""Generic value objects: frequency, power, time, geography.

Seed of the primitive catalog. This package must not import adapters, ORM,
or protocol modules. Production request paths stay unchanged until a later
authorized extraction task wires these types.
"""

from primitives.access import AccessClass, OrderedAccess, bind_request_class
from primitives.constraint import Constraint, ConstraintKind
from primitives.decision import Decision, DecisionAction, is_apply_write
from primitives.entitlement import ProtectionEntitlement
from primitives.frequency import FrequencyRange
from primitives.geography import GeoPoint, LinearRing, PointRadius, haversine_m
from primitives.power import PowerDbm, PowerMw, dbm_to_mw, mw_to_dbm
from primitives.preemption import class_preempts
from primitives.profile_context import ProfileContext
from primitives.request import SpectrumRequest, TransmissionFootprint
from primitives.time import TimeInterval, UtcInstant

__all__ = [
    "AccessClass",
    "Constraint",
    "ConstraintKind",
    "Decision",
    "DecisionAction",
    "FrequencyRange",
    "GeoPoint",
    "LinearRing",
    "PointRadius",
    "PowerDbm",
    "OrderedAccess",
    "PowerMw",
    "ProfileContext",
    "ProtectionEntitlement",
    "SpectrumRequest",
    "TimeInterval",
    "TransmissionFootprint",
    "UtcInstant",
    "bind_request_class",
    "class_preempts",
    "dbm_to_mw",
    "haversine_m",
    "is_apply_write",
    "mw_to_dbm",
]
