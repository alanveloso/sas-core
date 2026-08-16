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

__all__ = [
    "ADAPTER_API_VERSION",
    "AdapterKind",
    "ConsumerAdapter",
    "ConsumerView",
    "MappingDeviceAdapter",
    "MappingNetworkAdapter",
    "consumer_meets_requirements",
]
