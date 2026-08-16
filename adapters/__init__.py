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
from adapters.discovery import (
    ADAPTER_GROUPS,
    GROUP_DEVICE_ADAPTERS,
    GROUP_NETWORK_ADAPTERS,
    GROUP_PROTOCOL_ADAPTERS,
    AdapterDiscovery,
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
    "ADAPTER_GROUPS",
    "PROTOCOL_API_VERSION",
    "GENERIC_JSON_PROTOCOL_ID",
    "GROUP_DEVICE_ADAPTERS",
    "GROUP_NETWORK_ADAPTERS",
    "GROUP_PROTOCOL_ADAPTERS",
    "AdapterDiscovery",
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
