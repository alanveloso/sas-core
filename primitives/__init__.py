"""Generic value objects: frequency, power, time, geography.

Seed of the primitive catalog. This package must not import adapters, ORM,
or protocol modules. Production request paths stay unchanged until a later
authorized extraction task wires these types.
"""

from primitives.access import AccessClass, OrderedAccess, bind_request_class
from primitives.admission import evaluate_admission, power_exceeds
from primitives.authorization import (
    AuthorizedArea,
    ExclusionZone,
    FixedWindow,
    Lease,
    LeaseState,
)
from primitives.channelization import assignment_channels
from primitives.constraint import Constraint, ConstraintKind
from primitives.decision import Decision, DecisionAction, is_apply_write
from primitives.entitlement import ProtectionEntitlement
from primitives.frequency import FrequencyRange
from primitives.geography import GeoPoint, LinearRing, PointRadius, haversine_m
from primitives.power import PowerDbm, PowerMw, dbm_to_mw, mw_to_dbm
from primitives.preemption import class_preempts
from primitives.profile_context import ProfileContext
from primitives.registry import (
    MechanismAxis,
    MechanismContract,
    MechanismRegistry,
    builtin_mechanism_registry,
    select_optional_access,
)
from primitives.request import SpectrumRequest, TransmissionFootprint
from primitives.time import TimeInterval, UtcInstant

__all__ = [
    "AccessClass",
    "assignment_channels",
    "AuthorizedArea",
    "Constraint",
    "ConstraintKind",
    "Decision",
    "DecisionAction",
    "ExclusionZone",
    "FixedWindow",
    "FrequencyRange",
    "GeoPoint",
    "Lease",
    "LeaseState",
    "LinearRing",
    "MechanismAxis",
    "MechanismContract",
    "MechanismRegistry",
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
    "builtin_mechanism_registry",
    "class_preempts",
    "dbm_to_mw",
    "evaluate_admission",
    "haversine_m",
    "is_apply_write",
    "mw_to_dbm",
    "power_exceeds",
    "select_optional_access",
]
