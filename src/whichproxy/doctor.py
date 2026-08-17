from __future__ import annotations

from .env import (
    SAFE_NO_PROXY,
    ProxyEnv,
    dangerous_no_proxy_hits,
    read_user_env,
    redact_proxy,
    suggest_fix,
)
from .clinic import clinic_findings
from .probe import probe_local_proxy
from .match import ModelResult, consensus, evaluate

PRESETS = [
    "api.openai.com",
    "auth.openai.com",
    "chatgpt.com",
    "api.x.ai",
    "auth.x.ai",
    "api.anthropic.com",
    "claude.ai",
    "generativelanguage.googleapis.com",
    "api2.cursor.sh",
    "github.com",
]

_CLASH_CODEX_TIP = (
    "NO_PROXY contains AI vendor hosts. Token exchange may bypass Clash "
    "and get 403 unsupported_country_region_territory."
)
_NO_PROXY_TIP = "No HTTP_PROXY/HTTPS_PROXY set."
_USER_DRIFT_TIP = (
    "User-level NO_PROXY (new terminals) differs from this process. "
    "Fix the User variable or new windows will keep the old list."
)


def doctor_report(
    env: ProxyEnv,
    *,
    user_env: ProxyEnv | None = None,
    probe=None,
) -> dict:
    if user_env is None:
        user_env = read_user_env()
    if probe is None:
        probe = probe_local_proxy
    dangerous = dangerous_no_proxy_hits(env.no_proxy)
    user_dangerous = (
        dangerous_no_proxy_hits(user_env.no_proxy) if user_env is not None else []
    )
    hosts = [_host_entry(host, env) for host in PRESETS]
    tips: list[str] = []
    if dangerous or user_dangerous:
        tips.append(_CLASH_CODEX_TIP)
    if not env.effective_https:
        tips.append(_NO_PROXY_TIP)
    elif env.http_proxy and not env.https_proxy and not env.all_proxy:
        tips.append(
            "HTTP_PROXY is set but HTTPS_PROXY is empty. "
            "HTTPS (most AI CLIs) may skip the proxy."
        )
    elif env.https_proxy and not env.http_proxy and not env.all_proxy:
        tips.append(
            "HTTPS_PROXY is set but HTTP_PROXY is empty. "
            "Plain HTTP traffic may skip the proxy."
        )
    user_drift = bool(user_env is not None and user_env.no_proxy != env.no_proxy)
    if user_drift:
        tips.append(_USER_DRIFT_TIP)
    tips.append(f"Keep NO_PROXY local only: {SAFE_NO_PROXY}")
    reach = probe(env.effective_https)
    if reach.get("checked") and reach.get("ok") is False:
        tips.append(
            f"Proxy {reach.get('target')} is not accepting connections. "
            "Is Clash (or your mixed-port) running?"
        )
    payload = {
        "env": {
            "http_proxy": redact_proxy(env.http_proxy),
            "https_proxy": redact_proxy(env.https_proxy),
            "all_proxy": redact_proxy(env.all_proxy),
            "no_proxy": env.no_proxy,
        },
        "user_env": (
            {
                "http_proxy": redact_proxy(user_env.http_proxy),
                "https_proxy": redact_proxy(user_env.https_proxy),
                "all_proxy": redact_proxy(user_env.all_proxy),
                "no_proxy": user_env.no_proxy,
            }
            if user_env is not None
            else None
        ),
        "user_drift": user_drift,
        "dangerous": dangerous,
        "user_dangerous": user_dangerous,
        "hosts": hosts,
        "suggest": suggest_fix(env),
        "proxy": reach,
        "tips": tips,
    }
    payload["findings"] = clinic_findings(payload)
    return payload


def _host_entry(host: str, env: ProxyEnv) -> dict:
    results = evaluate(host, env)
    return {
        "host": host,
        "consensus": consensus(results),
        "models": [_model_dict(item, env) for item in results],
    }


def _model_dict(item: ModelResult, env: ProxyEnv) -> dict:
    return {
        "model": item.model,
        "route": item.route,
        "reason": _redact_reason(item.reason, env),
    }


def _redact_reason(reason: str, env: ProxyEnv) -> str:
    text = reason
    for raw in (env.http_proxy, env.https_proxy, env.all_proxy):
        if raw:
            hidden = redact_proxy(raw)
            if hidden != raw:
                text = text.replace(raw, hidden)
    return text
