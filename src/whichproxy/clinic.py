from __future__ import annotations

from .env import SAFE_NO_PROXY


def clinic_findings(report: dict) -> list[dict]:
    findings: list[dict] = []
    suggest = report.get("suggest") or suggest_fix_from_report(report)
    dangerous = list(report.get("dangerous") or [])
    user_dangerous = list(report.get("user_dangerous") or [])
    if dangerous:
        findings.append(
            _finding(
                "DANGEROUS_NOPROXY",
                "error",
                "当前终端的 NO_PROXY 含 AI 域名",
                "浏览器仍走 Clash，Codex / Claude / Grok 换 token 时会直连，常见 403 地区不支持。",
                extra="、".join(str(item) for item in dangerous),
                suggest=suggest,
            )
        )
    if user_dangerous:
        findings.append(
            _finding(
                "USER_DANGEROUS_NOPROXY",
                "error",
                "用户级 NO_PROXY（新开终端）含 AI 域名",
                "只改当前窗口不够，新开的终端还会带着旧名单。",
                extra="、".join(str(item) for item in user_dangerous),
                suggest=suggest,
                user_level=True,
            )
        )
    if report.get("user_drift"):
        findings.append(
            _finding(
                "USER_DRIFT",
                "warn",
                "用户级 NO_PROXY 和当前进程不一致",
                "新窗口会用另一套名单。以用户级为准修，或每个窗口单独 export。",
                suggest=suggest,
                user_level=True,
            )
        )
    env = report.get("env") or {}
    if not (env.get("https_proxy") or env.get("http_proxy") or env.get("all_proxy")):
        findings.append(
            _finding(
                "NO_PROXY_SERVER",
                "error",
                "没有设置 HTTP(S)_PROXY",
                "CLI 不知道 Clash 在哪。mixed-port 一般是 http://127.0.0.1:7897。",
                suggest=suggest,
            )
        )
    tips = " ".join(str(item) for item in (report.get("tips") or []))
    if "HTTPS_PROXY is empty" in tips:
        findings.append(
            _finding(
                "HTTPS_MISSING",
                "warn",
                "只设了 HTTP_PROXY，没有 HTTPS_PROXY",
                "多数 AI CLI 走 HTTPS，可能根本不进代理。",
                suggest=suggest,
            )
        )
    if "HTTP_PROXY is empty" in tips:
        findings.append(
            _finding(
                "HTTP_MISSING",
                "warn",
                "只设了 HTTPS_PROXY，没有 HTTP_PROXY",
                "少数工具的明文 HTTP 会直连。",
                suggest=suggest,
            )
        )
    disagree = [
        str(entry.get("host") or "")
        for entry in (report.get("hosts") or [])
        if entry.get("consensus") == "DISAGREE"
    ]
    direct = [
        str(entry.get("host") or "")
        for entry in (report.get("hosts") or [])
        if entry.get("consensus") == "DIRECT"
        and (env.get("https_proxy") or env.get("http_proxy") or env.get("all_proxy"))
    ]
    if disagree:
        findings.append(
            _finding(
                "HOST_DISAGREE",
                "error",
                "curl / Python / Go 对同一主机走法不一致",
                "典型就是 NO_PROXY 写了 openai.com：curl 仍走代理，Python 和 Go 直连。",
                extra="、".join(disagree),
                suggest=suggest,
            )
        )
    elif direct:
        findings.append(
            _finding(
                "HOST_DIRECT",
                "warn",
                "已设代理，但这些 AI 主机仍判定为直连",
                "检查 NO_PROXY 是否把它们放行了。",
                extra="、".join(direct),
                suggest=suggest,
            )
        )
    proxy = report.get("proxy") or {}
    if proxy.get("checked") and proxy.get("ok") is False:
        findings.append(
            _finding(
                "PROXY_DOWN",
                "error",
                f"本机代理 {proxy.get('target')} 没有在听",
                "环境变量对了也没用。先开 Clash，确认 mixed-port 和这个地址一致。",
                extra=_port_extra(report, proxy),
            )
        )
    if not findings:
        findings.append(
            _finding(
                "OK",
                "ok",
                "这一层看起来正常",
                f"NO_PROXY 应只留本机：{SAFE_NO_PROXY}",
                suggest=suggest,
            )
        )
    return findings


def render_clinic(report: dict) -> str:
    findings = clinic_findings(report)
    bad = [item for item in findings if item["level"] in {"error", "warn"}]
    lines = ["# whichproxy 诊所", ""]
    if any(item["level"] == "error" for item in findings):
        lines.append("结论：当前链路有问题，AI CLI 可能没走 Clash。")
    elif bad:
        lines.append("结论：能用，但有不一致，建议修一下。")
    else:
        lines.append("结论：这一层没有发现明显问题。")
    lines.append("")
    for index, item in enumerate(findings, start=1):
        lines.append(f"{index}. [{_level_zh(item['level'])}] {item['title']}")
        lines.append(f"   原因：{item['why']}")
        if item.get("extra"):
            lines.append(f"   细节：{item['extra']}")
        for command in item.get("commands") or []:
            lines.append(f"   {command}")
        lines.append("")
    lines.append("本工具只诊断、只打印命令，不会改任何环境变量。")
    lines.append("改用户级变量后，关掉旧终端再开新窗口。")
    return "\n".join(lines) + "\n"


def _port_extra(report: dict, proxy: dict) -> str:
    bits = [str(proxy.get("error") or "").strip()]
    live = [row for row in (report.get("ports") or []) if row.get("ok")]
    if live:
        labels = "、".join(f"{row['port']}（{row['label']}）" for row in live)
        bits.append(f"本机正在听：{labels}")
    return "；".join(item for item in bits if item)


def _level_zh(level: str) -> str:
    return {"error": "严重", "warn": "警告", "ok": "正常"}.get(level, level)


def suggest_fix_from_report(report: dict) -> dict:
    return dict(report.get("suggest") or {})


def _finding(
    code: str,
    level: str,
    title: str,
    why: str,
    *,
    extra: str = "",
    suggest: dict | None = None,
    user_level: bool = False,
) -> dict:
    commands: list[str] = []
    payload = suggest or {}
    if code != "PROXY_DOWN" and payload:
        if user_level and payload.get("user_powershell"):
            commands.append("用户级（新终端生效）：")
            commands.append(str(payload["user_powershell"]))
        if payload.get("powershell"):
            commands.append("本窗口 PowerShell：")
            commands.append(str(payload["powershell"]))
        if payload.get("bash"):
            commands.append("本窗口 bash：")
            commands.append(str(payload["bash"]))
        if payload.get("powershell_proxy") and code in {
            "NO_PROXY_SERVER",
            "HTTPS_MISSING",
            "HTTP_MISSING",
        }:
            commands.append("本窗口同时设三个代理变量：")
            commands.append(str(payload["powershell_proxy"]))
            if payload.get("bash_proxy"):
                commands.append(str(payload["bash_proxy"]))
    return {
        "code": code,
        "level": level,
        "title": title,
        "why": why,
        "extra": extra,
        "commands": commands,
    }
