"""Shared egress / SSRF guards for Admin-injected HTTP pulls (P8-003).

FAD peer pulls keep their stricter same-origin checks in ``fad_client_service``.
This module covers generic https URLs (federal DB sync, peer base URL inject).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_LITERAL_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata",
        "instance-data",
    }
)


class SsrfError(ValueError):
    """URL rejected by SSRF controls."""


def _host_allows_loopback_or_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return bool(ip.is_loopback or ip.is_private)
    except ValueError:
        return host in {"localhost", "localhost.localdomain"}


def _ip_blocked(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address, *, allow_lab: bool
) -> bool:
    if str(ip) in {"169.254.169.254", "169.254.169.253"}:
        return True
    if ip.is_multicast or ip.is_unspecified:
        return True
    if ip.is_link_local:
        return not allow_lab
    if ip.is_loopback:
        return not allow_lab
    if ip.is_private:
        return not allow_lab
    if ip.is_reserved:
        return True
    return False


def assert_https_egress_url_allowed(
    url: str, *, allow_lab_private: bool = True
) -> None:
    """Reject non-https, userinfo, metadata hosts, and blocked resolved IPs.

    When ``allow_lab_private`` is true, loopback/RFC1918 are allowed only if the
    hostname itself is loopback/private (lab/harness injects).
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise SsrfError(f"url must be https, got scheme={parsed.scheme!r}")
    if parsed.username is not None or parsed.password is not None:
        raise SsrfError("url must not include userinfo credentials")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise SsrfError("url missing host")
    if host in _BLOCKED_LITERAL_HOSTS:
        raise SsrfError(f"host blocked: {host}")

    allow_lab = bool(allow_lab_private and _host_allows_loopback_or_private(host))
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SsrfError(f"DNS resolution failed: {host}") from exc
    if not infos:
        raise SsrfError(f"DNS resolution empty: {host}")
    seen = False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        seen = True
        if _ip_blocked(ip, allow_lab=allow_lab):
            raise SsrfError(f"host resolves to blocked address {ip} (host={host})")
    if not seen:
        raise SsrfError(f"DNS produced no IPs: {host}")
