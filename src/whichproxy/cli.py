from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .clinic import render_clinic
from .doctor import _host_entry, doctor_report
from .env import ProxyEnv, read_env, redact_proxy, suggest_fix


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = _build_parser()
    args = parser.parse_args(argv)
    env = read_env()
    tokens: list[str] = args.targets
    if not tokens or tokens[0] in {"doctor", "clinic"}:
        return _cmd_doctor(env, json_mode=args.json)
    if tokens[0] == "env":
        return _cmd_env(env, json_mode=args.json)
    if tokens[0] == "suggest":
        return _cmd_suggest(env, json_mode=args.json)
    return _cmd_hosts(tokens, env, json_mode=args.json)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whichproxy",
        description=(
            "See whether a host uses your HTTP(S) proxy or slips through NO_PROXY."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "commands:\n"
            "  whichproxy HOST [HOST...]  route for each host\n"
            "  whichproxy env             print proxy-related environment variables\n"
            "  whichproxy doctor          中文诊所（默认）\n"
            "  whichproxy clinic          同 doctor\n"
            "  whichproxy suggest         打印安全 NO_PROXY（不改环境变量）\n"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"whichproxy {__version__}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="machine-readable JSON output",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        metavar="HOST",
        help="hosts to check, or 'env' / 'doctor' / 'suggest'",
    )
    return parser


def _cmd_env(env: ProxyEnv, json_mode: bool) -> int:
    payload = _env_payload(env)
    if json_mode:
        _print_json(payload)
    else:
        print(f"HTTP_PROXY={payload['http_proxy']}")
        print(f"HTTPS_PROXY={payload['https_proxy']}")
        print(f"ALL_PROXY={payload['all_proxy']}")
        print(f"NO_PROXY={payload['no_proxy']}")
    return 0


def _cmd_doctor(env: ProxyEnv, json_mode: bool) -> int:
    report = doctor_report(env)
    if json_mode:
        _print_json(report)
    else:
        print(render_clinic(report), end="")
        _print_doctor_hosts(report)
    proxy = report.get("proxy") or {}
    proxy_down = bool(proxy.get("checked") and proxy.get("ok") is False)
    failed = bool(report["dangerous"] or report.get("user_dangerous") or proxy_down)
    return 1 if failed else 0


def _cmd_suggest(env: ProxyEnv, json_mode: bool) -> int:
    payload = suggest_fix(env)
    if json_mode:
        _print_json(payload)
    else:
        print(f"NO_PROXY={payload['no_proxy']}")
        if payload["https_proxy"]:
            print(f"HTTPS_PROXY={payload['https_proxy']}")
        remove = payload["remove"]
        if remove:
            print("remove from NO_PROXY: " + ", ".join(str(item) for item in remove))
        print()
        print("本窗口 PowerShell：")
        print(f"  {payload['powershell']}")
        print("本窗口 bash：")
        print(f"  {payload['bash']}")
        print("用户级（新终端生效）：")
        print(f"  {payload['user_powershell']}")
        print()
        print("不会改任何环境变量。Does not write any environment variable.")
    return 0


def _cmd_hosts(hosts: list[str], env: ProxyEnv, json_mode: bool) -> int:
    entries = [_host_entry(host, env) for host in hosts]
    proxy_configured = bool(env.http_proxy or env.https_proxy or env.all_proxy)
    failed = False
    for entry in entries:
        decided = entry["consensus"]
        if decided == "DISAGREE" or (decided == "DIRECT" and proxy_configured):
            failed = True
    if json_mode:
        _print_json({"env": _env_payload(env), "hosts": entries})
    else:
        for index, entry in enumerate(entries):
            if index:
                print()
            _print_host_text(entry["host"], env, entry["models"], entry["consensus"])
    return 1 if failed else 0


def _print_doctor_hosts(report: dict) -> None:
    print()
    print("主机路由：")
    for entry in report["hosts"]:
        print(f"{entry['host']}  {entry['consensus']}")
        for item in entry["models"]:
            print(f"  {item['model']:<8}{item['route']}  ({item['reason']})")


def _print_host_text(host: str, env: ProxyEnv, models: list[dict], consensus: str | None = None) -> None:
    print(host)
    if consensus:
        print(f"  consensus={consensus}")
    print(f"  HTTP_PROXY={redact_proxy(env.http_proxy or env.https_proxy or env.all_proxy)}")
    print(f"  NO_PROXY={env.no_proxy}")
    for item in models:
        print(f"  {item['model']:<8}{item['route']}  ({item['reason']})")


def _env_payload(env: ProxyEnv) -> dict[str, str]:
    return {
        "http_proxy": redact_proxy(env.http_proxy),
        "https_proxy": redact_proxy(env.https_proxy),
        "all_proxy": redact_proxy(env.all_proxy),
        "no_proxy": env.no_proxy,
    }


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _ensure_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower()
        if encoding.replace("-", "") not in {"cp936", "gbk", "gb2312", "mbcs", "cp1252"}:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
