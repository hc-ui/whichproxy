from __future__ import annotations

import json
from typing import Any

import pytest

from whichproxy.cli import main

PROXY_URL = "http://127.0.0.1:7897"
AUTH_PROXY_URL = "http://user:s3cretPASS@127.0.0.1:7897"


def _combined(capsys: pytest.CaptureFixture[str]) -> str:
    captured = capsys.readouterr()
    return f"{captured.out}{captured.err}"


def _load_json(text: str) -> Any:
    blob = text.strip()
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        for index, char in enumerate(blob):
            if char in "{[":
                return json.loads(blob[index:])
        raise


def _set_clash_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    https_proxy: str = PROXY_URL,
    no_proxy: str = "localhost,openai.com",
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", https_proxy)
    monkeypatch.setenv("NO_PROXY", no_proxy)


def test_doctor_dangerous_noproxy_exits_1(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_clash_env(monkeypatch)
    code = main(["doctor"])
    text = _combined(capsys)
    assert code == 1
    assert "openai" in text.lower()


def test_no_args_runs_doctor(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_clash_env(monkeypatch)
    code = main([])
    text = _combined(capsys)
    assert code == 1
    assert "openai" in text.lower()


def test_host_api_openai_direct_exits_1(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_clash_env(monkeypatch)
    code = main(["api.openai.com"])
    text = _combined(capsys)
    assert code == 1
    assert "DIRECT" in text
    assert "consensus=" in text
    assert "api.openai.com" in text.lower()


def test_env_json_contains_redacted_fields(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_clash_env(monkeypatch, https_proxy=AUTH_PROXY_URL, no_proxy="localhost")
    code = main(["env", "--json"])
    text = _combined(capsys)
    payload = _load_json(text)
    dumped = json.dumps(payload)
    assert code == 0
    assert "s3cretPASS" not in text
    assert "s3cretPASS" not in dumped
    assert "***" in dumped


def test_suggest_prints_safe_noproxy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_clash_env(monkeypatch)
    code = main(["suggest"])
    text = _combined(capsys)
    assert code == 0
    assert "localhost,127.0.0.1,::1" in text
    assert "Does not write" in text
    assert "不会改" in text


def test_suggest_writes_script(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_clash_env(monkeypatch, no_proxy="localhost")
    out = tmp_path / "fix.ps1"
    code = main(["suggest", "-o", str(out)])
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert "NO_PROXY" in text
    assert "HTTPS_PROXY" in text


def test_ports_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from whichproxy import cli as cli_mod

    def fake_scan(**kwargs):
        del kwargs
        return [
            {"port": 7897, "label": "Clash mixed-port", "ok": True, "error": ""},
            {"port": 15721, "label": "CC Switch", "ok": False, "error": "refused"},
        ]

    monkeypatch.setattr(cli_mod, "scan_loopback_ports", fake_scan)
    code = main(["ports", "--json"])
    data = _load_json(_combined(capsys))
    assert code == 0
    assert data["ports"][0]["port"] == 7897


def test_clinic_alias_prints_chinese_diagnosis(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_clash_env(monkeypatch)
    code = main(["clinic"])
    text = _combined(capsys)
    assert code == 1
    assert "诊所" in text
    assert "openai" in text.lower()
    assert "PowerShell" in text
    assert "不一致" in text or "DISAGREE" in text
