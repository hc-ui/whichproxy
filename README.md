# whichproxy

Browser uses Clash. Codex / Claude still get `403 country not supported`.

Nine times out of ten, `NO_PROXY` contains `openai.com`. curl still goes through the proxy; Python and Go go **direct**. `whichproxy` prints that disagreement. It never sends a request.

[English](README.md) · [简体中文](README.zh-CN.md)

![whichproxy output: curl PROXY, python DIRECT, go DIRECT, marked DISAGREE](assets/disagree.svg)

## Warning

> [!WARNING]
> **Never** put `openai.com`, `.openai.com`, `api.openai.com`, `auth.openai.com`, `chatgpt.com`, or `.chatgpt.com` in `NO_PROXY`.
>
> That is what makes Codex / ChatGPT token exchange skip Clash.
>
> Keep `NO_PROXY` local only, for example:
>
> ```text
> localhost,127.0.0.1,::1
> ```

## Install

Python 3.10+, zero dependencies. Not on PyPI yet:

```bash
pip install git+https://github.com/hc-ui/whichproxy.git
```

Then run `whichproxy doctor` against your current shell.

## 20 seconds

Bad `NO_PROXY` (the usual Windows + Clash footgun):

```powershell
$env:HTTP_PROXY  = "http://127.0.0.1:7897"
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
$env:NO_PROXY    = "localhost,127.0.0.1,openai.com"
whichproxy api.openai.com
```

POSIX:

```bash
HTTP_PROXY=http://127.0.0.1:7897 \
HTTPS_PROXY=http://127.0.0.1:7897 \
NO_PROXY=localhost,127.0.0.1,openai.com \
whichproxy api.openai.com
```

```text
api.openai.com
  HTTP_PROXY=http://127.0.0.1:7897
  NO_PROXY=localhost,127.0.0.1,openai.com
  curl    PROXY   (via http://127.0.0.1:7897)
  python  DIRECT  (urllib proxy_bypass)
  go      DIRECT  (suffix openai.com)
```

curl only exact-matches a bare token; Python and Go treat `openai.com` as a suffix. The host is marked `DISAGREE`.

## Commands

| Command | What it does |
| --- | --- |
| `whichproxy HOST [HOST...]` | Route each host would take under curl / python / go |
| `whichproxy env` | Print proxy-related environment variables |
| `whichproxy doctor` | Check well-known AI hosts and warn about dangerous `NO_PROXY` entries |
| `whichproxy --json` | Same results, machine-readable |

`env` / `doctor` read `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY` (plus lowercase aliases).

## Matchers

Same `NO_PROXY` list, three models. The leading-dot difference is the whole point:

| Model | How it matches | `openai.com` (no dot) | `.openai.com` (leading dot) |
| --- | --- | --- | --- |
| **curl** | `*` = all hosts; no-dot = **exact** token; leading `.` = **subdomains only** | only `openai.com` — **not** `api.openai.com` | `api.openai.com`, **not** `openai.com` itself |
| **python** | `urllib.request.proxy_bypass_environment` — **suffix** match | `openai.com` **and** `api.openai.com` | same urllib rules (leading `.` is stripped, then suffix) |
| **go** | `*` = all; no-dot = that host **and** subdomains; leading `.` = **subdomains only**; CIDR for IPs | `openai.com` **and** `api.openai.com` | `api.openai.com`, **not** `openai.com` itself |

Disagreement is reported as `DISAGREE`, with each model's reason.

## Privacy

- **Local only.** Reads your environment. No network calls, no API keys, nothing uploaded.
- If a proxy URL contains `user:password`, the password is redacted in output.

## License

[MIT](LICENSE)
