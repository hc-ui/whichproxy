from __future__ import annotations

import fnmatch
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


def normalize_no_proxy_token(raw: str) -> str:
    """Strip ``[IPv6]`` brackets and a trailing ``:port`` from a NO_PROXY token.

    ``[::1]`` and ``127.0.0.1:8080`` appear in real env files; matching must
    use the host (or CIDR) curl/Go actually compare against.
    """
    text = (raw or "").strip()
    if text.startswith("[") and "]" in text:
        inner = text[1 : text.index("]")]
        rest = text[text.index("]") + 1 :]
        if rest.startswith("/") or not rest:
            return inner + rest
        if rest.startswith(":") and rest[1:].split("/", 1)[0].isdigit():
            suffix = rest.split(":", 1)[1]
            slash = suffix.find("/")
            return inner if slash < 0 else inner + suffix[slash:]
        return inner
    if "/" in text:
        return text
    if text.count(":") == 1 and not text.startswith(":"):
        host, port = text.rsplit(":", 1)
        if port.isdigit():
            return host
    return text


def _curl_match(host: str, tokens: list[str]) -> str | None:
    for token in tokens:
        raw = token.strip()
        if not raw:
            continue
        if raw == "*":
            return "matched *"
        # macOS / many tools ship ``*.local``; modern curl treats ``*`` as a wildcard.
        if "*" in raw:
            pattern = raw.lower().rstrip(".")
            if fnmatch.fnmatch(host, pattern):
                return f"wildcard {raw}"
            continue
        if raw.startswith("."):
            suffix = raw.lower().lstrip(".")
            if host.endswith("." + suffix):
                return f"subdomain of {raw}"
            continue
        lowered = normalize_no_proxy_token(raw).lower().rstrip(".")
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
                network = ipaddress.ip_network(normalize_no_proxy_token(raw), strict=False)
                addr = ipaddress.ip_address(host)
            except ValueError:
                continue
            if addr in network:
                return f"CIDR {raw}"
            continue
        lowered = normalize_no_proxy_token(raw).lower()
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
