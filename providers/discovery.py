"""Data provider discovery (G4-004). Not a process singleton."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

from adapters.discovery import GROUP_DATA_PROVIDERS
from providers.contract import (
    DATA_CAPABILITIES,
    PROVIDER_API_VERSION,
    DataProvider,
)


def _default_list_entry_points(group: str) -> Sequence[Any]:
    return tuple(entry_points(group=group))


@dataclass(frozen=True, slots=True)
class DataProviderDiscovery:
    overlays: Mapping[str, Any] = field(default_factory=dict)
    list_entry_points: Callable[[str], Sequence[Any]] = _default_list_entry_points

    def names(self) -> frozenset[str]:
        return frozenset(self._index())

    def load(self, name: str) -> DataProvider:
        if not name or not name.strip():
            raise ValueError("plugin name is required")
        index = self._index()
        if name not in index:
            raise ValueError(f"unknown data provider {name!r}")
        try:
            plugin = _materialize(index[name])
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"data provider {name!r} failed to load") from exc
        if not isinstance(plugin, DataProvider):
            raise ValueError(f"{name!r} is not a data provider")
        if plugin.api_version != PROVIDER_API_VERSION:
            raise ValueError(
                f"{name!r} api_version {plugin.api_version!r} incompatible with "
                f"{PROVIDER_API_VERSION!r}"
            )
        caps = plugin.advertised_capabilities()
        if plugin.kind.value not in caps:
            raise ValueError(f"{name!r} kind is not in advertised capabilities")
        if not caps.issubset(DATA_CAPABILITIES):
            raise ValueError(f"{name!r} advertised unknown data capabilities")
        return plugin

    def _index(self) -> dict[str, Any]:
        found: dict[str, Any] = {}
        for ep in self.list_entry_points(GROUP_DATA_PROVIDERS):
            ep_name = getattr(ep, "name", None)
            if not isinstance(ep_name, str) or not ep_name.strip():
                raise ValueError("entry point in data_providers is missing a name")
            if ep_name in found:
                raise ValueError(f"duplicate plugin name {ep_name!r}")
            found[ep_name] = ep.load
        for ov_name, factory in self.overlays.items():
            if ov_name in found:
                raise ValueError(f"duplicate plugin name {ov_name!r}")
            found[ov_name] = factory
        return found


def _materialize(factory: Any) -> Any:
    if not isinstance(factory, type) and not callable(factory):
        return factory
    target = factory() if not isinstance(factory, type) else factory
    if isinstance(target, type):
        return target()
    return target
