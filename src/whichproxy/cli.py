from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .doctor import _host_entry, doctor_report
from .env import ProxyEnv, read_env, redact_proxy


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = _build_parser()
    args = parser.parse_args(argv)
    env = read_env()
    tokens: list[str] = args.targets
    if not tokens or tokens[0] == "doctor":
        return _cmd_doctor(env, json_mode=args.json)
    if tokens[0] == "env":
        return _cmd_env(env, json_mode=args.json)
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
            "  whichproxy doctor          check well-known AI hosts (default)\n"
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
        help="hosts to check, or 'env' / 'doctor'",
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
        _print_doctor_text(report)
    return 1 if report["dangerous"] else 0


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
            _print_host_text(entry["host"], env, entry["models"])
    return 1 if failed else 0


def _print_doctor_text(report: dict) -> None:
    env = report["env"]
    print(f"HTTP_PROXY={env['http_proxy']}")
    print(f"HTTPS_PROXY={env['https_proxy']}")
    print(f"ALL_PROXY={env['all_proxy']}")
    print(f"NO_PROXY={env['no_proxy']}")
    print()
    dangerous = report["dangerous"]
    if dangerous:
        print("dangerous: " + ", ".join(dangerous))
    else:
        print("dangerous: (none)")
    print()
    for entry in report["hosts"]:
        print(f"{entry['host']}  {entry['consensus']}")
        for item in entry["models"]:
            print(f"  {item['model']:<8}{item['route']}  ({item['reason']})")
        print()
    tips = report["tips"]
    if tips:
        print("tips:")
        for tip in tips:
            print(f"  {tip}")


def _print_host_text(host: str, env: ProxyEnv, models: list[dict]) -> None:
    print(host)
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
        if encoding not in {"cp936", "gbk"}:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
