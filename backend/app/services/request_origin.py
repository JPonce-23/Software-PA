"""Resolve audit IPs from an unchanged socket peer and an explicit proxy chain.

Uvicorn must run with --no-proxy-headers: rewriting the ASGI peer first loses
the trust boundary. This helper neither authenticates users nor limits requests.
"""

from ipaddress import ip_address
from typing import Sequence


MAX_FORWARDED_CHARACTERS = 1024
MAX_FORWARDED_HOPS = 16


def _canonical_ip(value: str | None) -> str | None:
    if not value or "%" in value:
        return None
    try:
        address = ip_address(value)
    except ValueError:
        return None
    # Treat IPv4-mapped peers like their equivalent exact IPv4 configuration.
    mapped = getattr(address, "ipv4_mapped", None)
    return str(mapped if mapped is not None else address)


def resolve_client_ip(
    peer: str | None,
    forwarded_values: Sequence[str],
    trusted_proxy_ips: Sequence[str],
) -> str | None:
    """Use the nearest untrusted hop; ambiguous headers fall back to the peer.

    Every trusted proxy must append its actual peer or overwrite with a verified
    chain. Never configure client/NAT addresses as trusted proxy addresses.
    """
    peer = _canonical_ip(peer)
    if peer is None:
        return None
    trusted = {_canonical_ip(value) for value in trusted_proxy_ips}
    trusted.discard(None)
    if peer not in trusted or len(forwarded_values) != 1:
        return peer
    forwarded = forwarded_values[0]
    if (len(forwarded) > MAX_FORWARDED_CHARACTERS
            or any(ord(char) < 32 or ord(char) == 127 for char in forwarded)):
        return peer
    hops = forwarded.split(",")
    if len(hops) > MAX_FORWARDED_HOPS:
        return peer
    addresses = [_canonical_ip(hop.strip()) for hop in hops]
    if any(address is None for address in addresses):
        return peer
    for address in reversed(addresses):
        if address not in trusted:
            return address
    return peer
