from __future__ import annotations

import socket
from urllib.parse import urlsplit

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}

COMMON_PORTS = (
    (7897, "Clash mixed-port"),
    (7890, "Clash HTTP"),
    (7891, "Clash SOCKS"),
    (10809, "v2rayN HTTP"),
    (15721, "CC Switch"),
    (1080, "SOCKS"),
    (6152, "ClashX"),
)


def scan_loopback_ports(
    ports: tuple[tuple[int, str], ...] | None = None,
    timeout: float = 0.12,
    connect=None,
) -> list[dict]:
    """TCP-scan well-known local proxy ports. Never leaves the machine."""
    opener = connect or socket.create_connection
    rows: list[dict] = []
    for port, label in ports or COMMON_PORTS:
        ok = False
        error = ""
        try:
            with opener(("127.0.0.1", port), timeout):
                ok = True
        except OSError as exc:
            error = str(exc)
        rows.append({"port": port, "label": label, "ok": ok, "error": error})
    return rows


def first_live_proxy_url(rows: list[dict]) -> str:
    for row in rows:
        if row.get("ok"):
            return f"http://127.0.0.1:{int(row['port'])}"
    return ""


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
