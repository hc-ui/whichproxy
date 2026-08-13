# whichproxy

See if a host uses your HTTP(S) proxy or slips through `NO_PROXY`.

[English](README.md) · [简体中文](README.zh-CN.md)

## Why

On **Windows + Clash**, Codex / Claude / similar CLIs fail in a confusing way: the **browser** reaches OpenAI through the proxy, the **CLI** gets `403` *country, region, or territory not supported*.

The usual cause is `NO_PROXY` containing `openai.com` or `chatgpt.com`. The browser still goes through Clash; the CLI bypasses it and exits from your real region. Runtimes also **disagree** on what those tokens mean (`.openai.com` vs `openai.com`).

`whichproxy` prints the route **curl**, **Python**, and **Go** would each take. It does not send any requests.

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

Requires **Python 3.10+**. The package name is **`whichproxy`**. It is not published on PyPI yet — install from a clone:

```bash
pip install -e .
```

That installs the `whichproxy` command.

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
