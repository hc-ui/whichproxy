# Changelog

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
