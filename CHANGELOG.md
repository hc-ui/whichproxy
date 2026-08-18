# Changelog

## 0.4.0 — 2026-08-18

- `whichproxy ports` 扫描本机常见代理口（Clash / CC Switch / v2rayN）
- 当前代理没在听时，诊所会列出本机**正在听**的端口，并建议改用那个地址
- `doctor --copy` 把本窗口修复命令复制到剪贴板
- `suggest -o fix.ps1` 写出可点源的脚本，不改当前环境

## 0.3.1 — 2026-08-17

- 诊所标出 DISAGREE / 直连的主机
- `suggest` 同时给出 HTTP_PROXY / HTTPS_PROXY / ALL_PROXY 三连

## 0.3.0 — 2026-08-17

- `doctor` / `clinic` 输出中文诊所：问题、原因、可复制的 PowerShell/bash（不改环境变量）
- JSON 增加 `findings`

## 0.2.2 — 2026-08-17

- `doctor` TCP-probes loopback proxies (127.0.0.1 / localhost). No outbound request.

## 0.2.1 — 2026-08-17

- `doctor` warns if only `HTTP_PROXY` or only `HTTPS_PROXY` is set

## 0.2.0 — 2026-08-17

- `whichproxy suggest` prints a safe `NO_PROXY` and shell snippets; it does **not** write env
- `doctor` also checks User-level env on Windows and warns if it differs from this process
- Dangerous hosts now include x.ai, Anthropic, Gemini, and Cursor — not only OpenAI
- Suggested fix is local-only: `localhost,127.0.0.1,::1,.local`

## 0.1.1 — 2026-08-13

- Host output prints `consensus=`
- UTF-8 stdout also covers gb2312 / mbcs / cp1252

## 0.1.0 — 2026-08-13

First release.

- `whichproxy HOST [HOST...]` — show whether each host goes `PROXY`, `DIRECT`, or `NONE`
- Three `NO_PROXY` models: **curl**, **python** (`urllib.request.proxy_bypass_environment`), and **go**
- Flag `DISAGREE` when the models do not take the same route
- `whichproxy env` — print `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY`
- `whichproxy doctor` — check well-known AI hosts and warn on dangerous `NO_PROXY` entries (`openai.com`, `.openai.com`, `api.openai.com`, `auth.openai.com`, `chatgpt.com`, `.chatgpt.com`)
- `whichproxy --json` — machine-readable output
- Local only: no live HTTP checks, no API keys, nothing uploaded
- Redact passwords in proxy URLs
- MIT license
