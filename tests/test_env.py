from __future__ import annotations

import pytest

from whichproxy.env import dangerous_no_proxy_hits, read_env, redact_proxy

PROXY_URL = "http://127.0.0.1:7897"
AUTH_PROXY_URL = "http://user:s3cretPASS@127.0.0.1:7897"
REDACTED_AUTH_PROXY = "http://user:***@127.0.0.1:7897"


def test_read_env_uses_mapping_not_process_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://SHOULD-NOT-SEE:1")
    monkeypatch.setenv("NO_PROXY", "evil.com")
    env = read_env({"HTTPS_PROXY": PROXY_URL, "NO_PROXY": "localhost"})
    assert env.https_proxy == PROXY_URL
    assert env.no_proxy == "localhost"
    assert "SHOULD-NOT-SEE" not in env.https_proxy


def test_read_env_defaults_to_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "localhost")
    env = read_env()
    assert env.https_proxy == PROXY_URL
    assert env.no_proxy == "localhost"


def test_redact_proxy_hides_password() -> None:
    assert redact_proxy(AUTH_PROXY_URL) == REDACTED_AUTH_PROXY
    assert "s3cretPASS" not in redact_proxy(AUTH_PROXY_URL)


def test_redact_proxy_leaves_plain_url() -> None:
    assert redact_proxy(PROXY_URL) == PROXY_URL


def test_dangerous_no_proxy_hits_finds_openai() -> None:
    hits = dangerous_no_proxy_hits("localhost,openai.com,127.0.0.1")
    assert "openai.com" in hits


def test_dangerous_no_proxy_hits_finds_related_tokens() -> None:
    raw = "localhost,.openai.com,api.openai.com,chatgpt.com"
    hits = dangerous_no_proxy_hits(raw)
    assert ".openai.com" in hits
    assert "api.openai.com" in hits
    assert "chatgpt.com" in hits


def test_dangerous_no_proxy_hits_ignores_unrelated() -> None:
    assert dangerous_no_proxy_hits("localhost,127.0.0.1,.local") == []
