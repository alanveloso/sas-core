"""Adapter plugin discovery via entry points (G4-003).

Third-party packages publish groups under ``spectrum_access.*`` without editing
Coordination Core. Data providers load via ``providers.discovery``.
RF/mechanism groups remain reserved names only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

from adapters.device import (
    ADAPTER_API_VERSION,
    AdapterKind,
    ConsumerAdapter,
)
from adapters.protocol import PROTOCOL_API_VERSION, ProtocolAdapter

GROUP_DEVICE_ADAPTERS = "spectrum_access.device_adapters"
GROUP_NETWORK_ADAPTERS = "spectrum_access.network_adapters"
GROUP_PROTOCOL_ADAPTERS = "spectrum_access.protocol_adapters"
GROUP_MECHANISMS = "spectrum_access.mechanisms"
GROUP_DATA_PROVIDERS = "spectrum_access.data_providers"
GROUP_RF_MODELS = "spectrum_access.rf_models"

ADAPTER_GROUPS = frozenset(
    {
        GROUP_DEVICE_ADAPTERS,
        GROUP_NETWORK_ADAPTERS,
        GROUP_PROTOCOL_ADAPTERS,
    }
)

RESERVED_GROUPS = ADAPTER_GROUPS | frozenset({GROUP_MECHANISMS, GROUP_RF_MODELS})


def _default_list_entry_points(group: str) -> Sequence[Any]:
    return tuple(entry_points(group=group))


@dataclass(frozen=True, slots=True)
class AdapterDiscovery:
    """Per-call discovery. Not a process-wide singleton."""

    overlays: Mapping[str, Mapping[str, type]] = field(default_factory=dict)
    list_entry_points: Callable[[str], Sequence[Any]] = _default_list_entry_points

    def names(self, group: str) -> frozenset[str]:
        return frozenset(self._index(group))

    def load(self, group: str, name: str) -> Any:
        if not name or not name.strip():
            raise ValueError("plugin name is required")
        index = self._index(group)
        if name not in index:
            raise ValueError(f"unknown plugin {name!r} in group {group}")
        factory = index[name]
        try:
            plugin = self._materialize(factory)
        except TypeError as exc:
            raise ValueError(f"plugin {name!r} is not a zero-argument factory") from exc
        self._validate(group, name, plugin)
        return plugin

    @staticmethod
    def _materialize(factory: Any) -> Any:
        target = factory() if not isinstance(factory, type) else factory
        if isinstance(target, type):
            return target()
        return target

    def _index(self, group: str) -> dict[str, Any]:
        if group not in ADAPTER_GROUPS:
            raise ValueError(f"unsupported adapter group: {group}")
        found: dict[str, Any] = {}
        for ep in self.list_entry_points(group):
            ep_name = getattr(ep, "name", None)
            if not isinstance(ep_name, str) or not ep_name.strip():
                raise ValueError(f"entry point in {group} is missing a name")
            if ep_name in found:
                raise ValueError(f"duplicate plugin name {ep_name!r} in {group}")
            found[ep_name] = ep.load
        overlay = self.overlays.get(group, {})
        for ov_name, factory in overlay.items():
            if ov_name in found:
                raise ValueError(f"duplicate plugin name {ov_name!r} in {group}")
            found[ov_name] = factory
        return found

    def _validate(self, group: str, name: str, plugin: Any) -> None:
        if group == GROUP_PROTOCOL_ADAPTERS:
            if not isinstance(plugin, ProtocolAdapter):
                raise ValueError(f"{name!r} is not a protocol adapter")
            if plugin.api_version != PROTOCOL_API_VERSION:
                raise ValueError(
                    f"{name!r} protocol api_version {plugin.api_version!r} "
                    f"incompatible with {PROTOCOL_API_VERSION!r}"
                )
            if not plugin.protocol_id.strip():
                raise ValueError(f"{name!r} protocol_id is required")
            return
        if not isinstance(plugin, ConsumerAdapter):
            raise ValueError(f"{name!r} is not a consumer adapter")
        if plugin.api_version != ADAPTER_API_VERSION:
            raise ValueError(
                f"{name!r} adapter api_version {plugin.api_version!r} "
                f"incompatible with {ADAPTER_API_VERSION!r}"
            )
        expected = (
            AdapterKind.DEVICE
            if group == GROUP_DEVICE_ADAPTERS
            else AdapterKind.NETWORK
        )
        if plugin.kind is not expected:
            raise ValueError(
                f"{name!r} kind {plugin.kind!r} does not match group {group}"
            )
