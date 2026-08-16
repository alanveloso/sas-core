"""Device, network, and protocol adapters (G4/G5)."""

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
from adapters.winnforum_rest import (
    WINNFORUM_REST_PROTOCOL_ID,
    WinnForumRestProtocolAdapter,
    winnforum_rest_protocol_adapter,
)

__all__ = [
    "ADAPTER_API_VERSION",
    "ADAPTER_GROUPS",
    "PROTOCOL_API_VERSION",
    "GENERIC_JSON_PROTOCOL_ID",
    "WINNFORUM_REST_PROTOCOL_ID",
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
    "WinnForumRestProtocolAdapter",
    "consumer_meets_requirements",
    "winnforum_rest_protocol_adapter",
]
