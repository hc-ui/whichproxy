from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .clipboard import copy_text
from .clinic import render_clinic
from .doctor import _host_entry, doctor_report
from .env import ProxyEnv, read_env, redact_proxy, suggest_fix
from .probe import scan_loopback_ports


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = _build_parser()
    args = parser.parse_args(argv)
    env = read_env()
    tokens: list[str] = args.targets
    if not tokens or tokens[0] in {"doctor", "clinic"}:
        return _cmd_doctor(env, json_mode=args.json, copy=args.copy)
    if tokens[0] == "env":
        return _cmd_env(env, json_mode=args.json)
    if tokens[0] == "suggest":
        return _cmd_suggest(env, json_mode=args.json, copy=args.copy, out=args.out)
    if tokens[0] == "ports":
        return _cmd_ports(json_mode=args.json)
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
            "  whichproxy ports           扫描本机常见代理端口\n"
            "  whichproxy doctor --copy   诊断并把修复命令复制到剪贴板\n"
            "  whichproxy suggest -o t.ps1  写出本窗口脚本，点源即可\n"
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
        "--copy",
        action="store_true",
        help="把本窗口修复命令复制到剪贴板（不改环境变量）",
    )
    parser.add_argument(
        "-o",
        "--out",
        default=None,
        metavar="FILE",
        help="suggest 时写出 .ps1 / .sh，不改当前环境",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        metavar="HOST",
        help="hosts to check, or 'env' / 'doctor' / 'suggest' / 'ports'",
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


def _cmd_doctor(env: ProxyEnv, json_mode: bool, copy: bool = False) -> int:
    report = doctor_report(env)
    if json_mode:
        _print_json(report)
    else:
        print(render_clinic(report), end="")
        _print_doctor_hosts(report)
        _print_live_ports(report.get("ports") or [])
    if copy:
        _copy_or_warn(str((report.get("suggest") or {}).get("script_ps1") or ""))
    proxy = report.get("proxy") or {}
    proxy_down = bool(proxy.get("checked") and proxy.get("ok") is False)
    failed = bool(report["dangerous"] or report.get("user_dangerous") or proxy_down)
    return 1 if failed else 0


def _cmd_suggest(
    env: ProxyEnv,
    json_mode: bool,
    copy: bool = False,
    out: str | None = None,
) -> int:
    report = doctor_report(env)
    payload = report.get("suggest") or suggest_fix(env)
    if out:
        path_text = str(payload.get("script_ps1") or "")
        from pathlib import Path

        path = Path(out).expanduser()
        path.write_text(path_text, encoding="utf-8", newline="\n")
        print(f"wrote {path}")
        print("本窗口执行：. .\\" + path.name if path.suffix.lower() == ".ps1" else f"source {path}")
        return 0
    if json_mode:
        _print_json(payload)
        return 0
    print(f"NO_PROXY={payload['no_proxy']}")
    if payload["https_proxy"]:
        print(f"HTTPS_PROXY={payload['https_proxy']}")
    remove = payload["remove"]
    if remove:
        print("remove from NO_PROXY: " + ", ".join(str(item) for item in remove))
    print()
    print("本窗口 PowerShell：")
    print(f"  {payload['powershell']}")
    if payload.get("powershell_proxy"):
        print(f"  {payload['powershell_proxy']}")
    print("本窗口 bash：")
    print(f"  {payload['bash']}")
    if payload.get("bash_proxy"):
        print(f"  {payload['bash_proxy']}")
    print("用户级（新终端生效）：")
    print(f"  {payload['user_powershell']}")
    print()
    print("不会改任何环境变量。Does not write any environment variable.")
    if copy:
        _copy_or_warn(str(payload.get("script_ps1") or ""))
    return 0


def _cmd_ports(json_mode: bool) -> int:
    rows = scan_loopback_ports()
    if json_mode:
        _print_json({"ports": rows})
        return 0 if any(row.get("ok") for row in rows) else 1
    live = [row for row in rows if row.get("ok")]
    if not live:
        print("本机常见代理端口都没在听。先开 Clash / CC Switch。")
        return 1
    print("本机正在听：")
    for row in live:
        print(f"  {row['port']:<6} {row['label']}")
    dead = [row for row in rows if not row.get("ok")]
    if dead:
        print("未开：")
        for row in dead:
            print(f"  {row['port']:<6} {row['label']}")
    return 0


def _print_live_ports(rows: list) -> None:
    live = [row for row in rows if row.get("ok")]
    if not live:
        return
    print()
    print("本机代理端口：")
    for row in live:
        print(f"  {row['port']:<6} {row['label']}")


def _copy_or_warn(text: str) -> None:
    if not text.strip():
        print("没有可复制的修复命令。", file=sys.stderr)
        return
    try:
        copy_text(text)
    except OSError as exc:
        print(f"无法复制到剪贴板：{exc}", file=sys.stderr)
        return
    print("已复制本窗口修复命令到剪贴板。")


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
