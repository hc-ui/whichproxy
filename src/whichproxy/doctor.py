from __future__ import annotations

from .env import ProxyEnv, dangerous_no_proxy_hits, redact_proxy
from .match import ModelResult, consensus, evaluate

PRESETS = [
    "api.openai.com",
    "auth.openai.com",
    "openai.com",
    "chatgpt.com",
    "api.x.ai",
    "api.anthropic.com",
    "github.com",
]

_CLASH_CODEX_TIP = (
    "NO_PROXY contains OpenAI hosts. Codex token exchange may bypass Clash "
    "and get 403 unsupported_country_region_territory."
)
_NO_PROXY_TIP = "No HTTP_PROXY/HTTPS_PROXY set."


def doctor_report(env: ProxyEnv) -> dict:
    dangerous = dangerous_no_proxy_hits(env.no_proxy)
    hosts = [_host_entry(host, env) for host in PRESETS]
    tips: list[str] = []
    if dangerous:
        tips.append(_CLASH_CODEX_TIP)
    if not env.effective_https:
        tips.append(_NO_PROXY_TIP)
    return {
        "env": {
            "http_proxy": redact_proxy(env.http_proxy),
            "https_proxy": redact_proxy(env.https_proxy),
            "all_proxy": redact_proxy(env.all_proxy),
            "no_proxy": env.no_proxy,
        },
        "dangerous": dangerous,
        "hosts": hosts,
        "tips": tips,
    }


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
