from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


DANGEROUS_NOPROXY = (
    "openai.com",
    ".openai.com",
    "api.openai.com",
    "auth.openai.com",
    "chatgpt.com",
    ".chatgpt.com",
)


@dataclass(frozen=True)
class ProxyEnv:
    http_proxy: str
    https_proxy: str
    all_proxy: str
    no_proxy: str

    @property
    def effective_https(self) -> str:
        return self.https_proxy or self.http_proxy or self.all_proxy

    @property
    def effective_http(self) -> str:
        return self.http_proxy or self.all_proxy or self.https_proxy

    def tokens(self) -> list[str]:
        return split_no_proxy(self.no_proxy)


def split_no_proxy(raw: str) -> list[str]:
    parts: list[str] = []
    for chunk in (raw or "").replace(";", ",").split(","):
        original = chunk.strip()
        if original:
            parts.append(original)
    return parts


def read_env(environ: dict[str, str] | None = None) -> ProxyEnv:
    env = environ if environ is not None else os.environ
    return ProxyEnv(
        http_proxy=_first(env, "HTTP_PROXY", "http_proxy"),
        https_proxy=_first(env, "HTTPS_PROXY", "https_proxy"),
        all_proxy=_first(env, "ALL_PROXY", "all_proxy"),
        no_proxy=_first(env, "NO_PROXY", "no_proxy"),
    )


def _first(env: dict[str, str], *names: str) -> str:
    for name in names:
        value = env.get(name)
        if value:
            return value.strip()
    return ""


def redact_proxy(url: str) -> str:
    if not url or "@" not in url:
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not parts.username and not parts.password:
        return url
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    user = parts.username or ""
    auth = f"{user}:***" if user or parts.password else ""
    netloc = f"{auth}@{host}" if auth else host
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def dangerous_no_proxy_hits(no_proxy: str) -> list[str]:
    hits: list[str] = []
    for token in split_no_proxy(no_proxy):
        lowered = token.lower().lstrip("*").lstrip(".")
        for bad in DANGEROUS_NOPROXY:
            needle = bad.lstrip(".")
            if lowered == needle or lowered.endswith("." + needle):
                hits.append(token)
                break
    return hits
