# Changelog

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
