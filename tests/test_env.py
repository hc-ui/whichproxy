from __future__ import annotations

import pytest

from whichproxy.env import (
    SAFE_NO_PROXY,
    ProxyEnv,
    dangerous_no_proxy_hits,
    read_env,
    read_user_env,
    redact_proxy,
    suggest_fix,
)

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


def test_dangerous_no_proxy_hits_finds_xai_and_anthropic() -> None:
    hits = dangerous_no_proxy_hits("localhost,x.ai,api.anthropic.com,cursor.com")
    assert "x.ai" in hits
    assert "api.anthropic.com" in hits
    assert "cursor.com" in hits


def test_suggest_fix_does_not_write_and_keeps_local_only() -> None:
    env = read_env({"HTTPS_PROXY": PROXY_URL, "NO_PROXY": "localhost,openai.com"})
    payload = suggest_fix(env)
    assert payload["no_proxy"] == SAFE_NO_PROXY
    assert "openai.com" in payload["remove"]
    assert "openai.com" not in str(payload["no_proxy"])
    assert "ALL_PROXY" in str(payload["powershell_proxy"])


def test_suggest_fix_prefers_listening_port_when_current_down() -> None:
    env = read_env({"HTTPS_PROXY": "http://127.0.0.1:7897", "NO_PROXY": "localhost"})
    listening = [
        {"port": 7897, "label": "Clash", "ok": False, "error": "refused"},
        {"port": 15721, "label": "CC Switch", "ok": True, "error": ""},
    ]
    payload = suggest_fix(env, listening=listening, current_ok=False)
    assert payload["https_proxy"] == "http://127.0.0.1:15721"
    assert "15721" in str(payload["script_ps1"])


def test_read_user_env_accepts_injected_mapping() -> None:
    env = read_user_env({"NO_PROXY": "openai.com", "HTTPS_PROXY": PROXY_URL})
    assert env is not None
    assert env.no_proxy == "openai.com"


def test_doctor_report_flags_user_drift() -> None:
    from whichproxy.doctor import doctor_report

    process = read_env({"HTTPS_PROXY": PROXY_URL, "NO_PROXY": "localhost"})
    user = ProxyEnv("", PROXY_URL, "", "localhost,openai.com")
    report = doctor_report(process, user_env=user)
    assert report["user_drift"] is True
    assert "openai.com" in report["user_dangerous"]
    assert report["suggest"]["no_proxy"] == SAFE_NO_PROXY


def test_doctor_warns_when_only_http_proxy_set() -> None:
    from whichproxy.doctor import doctor_report

    env = read_env({"HTTP_PROXY": PROXY_URL, "NO_PROXY": "localhost"})
    report = doctor_report(env, user_env=env)
    joined = " ".join(report["tips"])
    assert "HTTPS_PROXY is empty" in joined


def test_doctor_reports_dead_loopback_proxy() -> None:
    from whichproxy.doctor import doctor_report

    env = read_env({"HTTPS_PROXY": PROXY_URL, "NO_PROXY": "localhost"})

    def fake_probe(url: str) -> dict:
        return {
            "checked": True,
            "ok": False,
            "target": "127.0.0.1:7897",
            "error": "refused",
        }

    report = doctor_report(env, user_env=env, probe=fake_probe)
    assert report["proxy"]["ok"] is False
    assert any("not accepting connections" in tip for tip in report["tips"])
