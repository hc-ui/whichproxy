"""Isolate tests from the real process environment."""

from __future__ import annotations

import pytest

PROXY_ENV_NAMES = (
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
)


@pytest.fixture(autouse=True)
def isolate_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop proxy-related env vars so tests never see the user's Clash settings."""
    for name in PROXY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
