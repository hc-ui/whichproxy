from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.request import proxy_bypass_environment

from .env import ProxyEnv, split_no_proxy


@dataclass(frozen=True)
class ModelResult:
    model: str
    route: str  # PROXY | DIRECT | NONE
    reason: str


def normalize_host(value: str) -> str:
    text = (value or "").strip()
    if "://" in text:
        text = urlsplit(text).hostname or text
    if text.startswith("[") and "]" in text:
        text = text[1 : text.index("]")]
    if text.count(":") == 1 and not text.startswith(":"):
        host, maybe_port = text.rsplit(":", 1)
        if maybe_port.isdigit():
            text = host
    return text.strip(".").lower()


def evaluate(host: str, env: ProxyEnv) -> list[ModelResult]:
    host_n = normalize_host(host)
    proxy = env.effective_https
    if not proxy and not env.no_proxy:
        return [
            ModelResult("curl", "NONE", "no HTTP_PROXY/HTTPS_PROXY/ALL_PROXY"),
            ModelResult("python", "NONE", "no HTTP_PROXY/HTTPS_PROXY/ALL_PROXY"),
            ModelResult("go", "NONE", "no HTTP_PROXY/HTTPS_PROXY/ALL_PROXY"),
        ]
    tokens = env.tokens()
    return [
        _curl(host_n, tokens, proxy),
        _python(host_n, env, proxy),
        _go(host_n, tokens, proxy),
    ]


def consensus(results: list[ModelResult]) -> str:
    routes = {item.route for item in results}
    if len(routes) == 1:
        return next(iter(routes))
    return "DISAGREE"


def _direct_or_proxy(matched: str | None, proxy: str) -> tuple[str, str]:
    if matched:
        return "DIRECT", matched
    if proxy:
        return "PROXY", f"via {proxy}"
    return "NONE", "no proxy configured"


def _curl(host: str, tokens: list[str], proxy: str) -> ModelResult:
    reason = _curl_match(host, tokens)
    route, detail = _direct_or_proxy(reason, proxy)
    return ModelResult("curl", route, detail)


def _curl_match(host: str, tokens: list[str]) -> str | None:
    for token in tokens:
        raw = token.strip()
        if not raw:
            continue
        if raw == "*":
            return "matched *"
        if raw.startswith("."):
            suffix = raw.lower().lstrip(".")
            if host.endswith("." + suffix):
                return f"subdomain of {raw}"
            continue
        lowered = raw.lower().rstrip(".")
        if host == lowered:
            return f"exact {raw}"
    return None


def _python(host: str, env: ProxyEnv, proxy: str) -> ModelResult:
    try:
        bypass = bool(proxy_bypass_environment(host, {"no": env.no_proxy}))
    except Exception as exc:  # pragma: no cover - urllib edge
        return ModelResult("python", "PROXY" if proxy else "NONE", f"urllib error: {exc}")
    if bypass:
        return ModelResult("python", "DIRECT", "urllib proxy_bypass")
    route, detail = _direct_or_proxy(None, proxy)
    return ModelResult("python", route, detail)


def _go(host: str, tokens: list[str], proxy: str) -> ModelResult:
    reason = _go_match(host, tokens)
    route, detail = _direct_or_proxy(reason, proxy)
    return ModelResult("go", route, detail)


def _go_match(host: str, tokens: list[str]) -> str | None:
    for token in tokens:
        raw = token.strip()
        if not raw:
            continue
        if raw == "*":
            return "matched *"
        if "/" in raw:
            try:
                network = ipaddress.ip_network(raw, strict=False)
                addr = ipaddress.ip_address(host)
            except ValueError:
                continue
            if addr in network:
                return f"CIDR {raw}"
            continue
        lowered = raw.lower()
        if lowered.startswith("."):
            suffix = lowered.lstrip(".")
            if host.endswith("." + suffix):
                return f"subdomain of {raw}"
            continue
        if host == lowered or host.endswith("." + lowered):
            return f"suffix {raw}"
    return None


def split_tokens(raw: str) -> list[str]:
    return split_no_proxy(raw)
