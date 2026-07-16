from __future__ import annotations

import ipaddress
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import HTTPException, status

TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_base_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("base_url must be an absolute HTTP(S) URL")
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def _reject_private_ip_literal(hostname: str) -> None:
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Private or reserved IP URLs are not allowed")


def canonicalize_url(raw_url: str, site_base_url: str) -> str:
    parts = urlsplit(raw_url)
    base = urlsplit(site_base_url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="URL must be absolute HTTP(S)")
    _reject_private_ip_literal(parts.hostname)
    if parts.hostname.lower() != (base.hostname or "").lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"URL host must match site host: {base.hostname}",
        )

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_KEYS and not key.lower().startswith(TRACKING_PREFIXES)
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(("https", parts.netloc.lower(), path, urlencode(query, doseq=True), ""))
