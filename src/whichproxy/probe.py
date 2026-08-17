from __future__ import annotations

import socket
from urllib.parse import urlsplit

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def probe_local_proxy(url: str, timeout: float = 0.4) -> dict:
    """TCP-connect to a loopback proxy. Never talks to the public internet."""
    if not (url or "").strip():
        return {"checked": False, "ok": None, "target": "", "error": "no proxy"}
    raw = url.strip()
    try:
        parts = urlsplit(raw if "://" in raw else "http://" + raw)
    except ValueError:
        return {"checked": False, "ok": None, "target": raw, "error": "bad url"}
    host = (parts.hostname or "").lower()
    port = parts.port or (443 if parts.scheme == "https" else 80)
    target = f"{host}:{port}"
    if host not in _LOOPBACK:
        return {
            "checked": False,
            "ok": None,
            "target": target,
            "error": "not loopback",
        }
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"checked": True, "ok": True, "target": target, "error": ""}
    except OSError as exc:
        return {
            "checked": True,
            "ok": False,
            "target": target,
            "error": str(exc),
        }
