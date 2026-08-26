from __future__ import annotations

from whichproxy.env import ProxyEnv, read_env
from whichproxy.match import ModelResult, evaluate, normalize_host

PROXY_URL = "http://127.0.0.1:7897"


def _env(no_proxy: str) -> ProxyEnv:
    return read_env({"HTTPS_PROXY": PROXY_URL, "NO_PROXY": no_proxy})


def _by_model(host: str, no_proxy: str) -> dict[str, ModelResult]:
    return {item.model: item for item in evaluate(host, _env(no_proxy))}


def test_curl_dot_openai_matches_subdomain_not_apex() -> None:
    sub = _by_model("api.openai.com", ".openai.com")
    apex = _by_model("openai.com", ".openai.com")
    assert sub["curl"].route == "DIRECT"
    assert apex["curl"].route == "PROXY"


def test_python_openai_suffix_matches_api_subdomain() -> None:
    results = _by_model("api.openai.com", "openai.com")
    assert results["python"].route == "DIRECT"


def test_go_dot_openai_matches_subdomain_not_apex() -> None:
    apex = _by_model("openai.com", ".openai.com")
    sub = _by_model("api.openai.com", ".openai.com")
    assert apex["go"].route == "PROXY"
    assert sub["go"].route == "DIRECT"


def test_go_bare_openai_matches_apex_and_subdomain() -> None:
    apex = _by_model("openai.com", "openai.com")
    sub = _by_model("api.openai.com", "openai.com")
    assert apex["go"].route == "DIRECT"
    assert sub["go"].route == "DIRECT"


def test_curl_cidr_matches_like_modern_curl() -> None:
    inside = _by_model("10.0.0.8", "10.0.0.0/8")
    outside = _by_model("11.1.1.1", "10.0.0.0/8")
    assert inside["curl"].route == "DIRECT"
    assert "CIDR" in inside["curl"].reason
    assert outside["curl"].route == "PROXY"


def test_curl_ipv6_cidr_matches_like_modern_curl() -> None:
    inside = _by_model("[fd00::1]", "fd00::/8")
    outside = _by_model("[2001:db8::1]", "fd00::/8")
    assert inside["curl"].route == "DIRECT"
    assert "CIDR" in inside["curl"].reason
    assert outside["curl"].route == "PROXY"


def test_star_matches_all_curl_and_go_direct() -> None:
    results = _by_model("api.openai.com", "*")
    assert results["curl"].route == "DIRECT"
    assert results["go"].route == "DIRECT"
    assert "matched *" in results["curl"].reason
    assert "matched *" in results["go"].reason


def test_normalize_host_strips_https_and_port() -> None:
    assert normalize_host("https://api.openai.com") == "api.openai.com"
    assert normalize_host("https://api.openai.com:443") == "api.openai.com"
    assert normalize_host("api.openai.com:443") == "api.openai.com"
    assert normalize_host("HTTPS://API.OpenAI.com:443/v1") == "api.openai.com"


def test_evaluate_applies_normalize_host() -> None:
    results = {item.model: item for item in evaluate("https://api.openai.com:443", _env(".openai.com"))}
    assert results["curl"].route == "DIRECT"
    assert results["go"].route == "DIRECT"
