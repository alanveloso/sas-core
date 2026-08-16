"""Device and network consumer adapters (G4)."""

from adapters.device import (
    ADAPTER_API_VERSION,
    AdapterKind,
    ConsumerAdapter,
    ConsumerView,
    MappingDeviceAdapter,
    MappingNetworkAdapter,
    consumer_meets_requirements,
)
from adapters.protocol import (
    GENERIC_JSON_PROTOCOL_ID,
    PROTOCOL_API_VERSION,
    DomainOperation,
    GenericJsonProtocolAdapter,
    ProtocolAdapter,
    ProtocolInbound,
)

__all__ = [
    "ADAPTER_API_VERSION",
    "PROTOCOL_API_VERSION",
    "GENERIC_JSON_PROTOCOL_ID",
    "AdapterKind",
    "ConsumerAdapter",
    "ConsumerView",
    "DomainOperation",
    "GenericJsonProtocolAdapter",
    "MappingDeviceAdapter",
    "MappingNetworkAdapter",
    "ProtocolAdapter",
    "ProtocolInbound",
    "consumer_meets_requirements",
]
