# whichproxy spec (v0.1)

See whether a host will use your HTTP(S) proxy or slip through `NO_PROXY`.

## Why

On Windows + Clash, AI CLIs (Codex, Claude, Grok) often fail in a confusing way:
the browser uses the proxy, the CLI does not. The usual cause is `NO_PROXY`
containing `openai.com` / `chatgpt.com`. Different runtimes match `NO_PROXY`
differently. This tool prints the route each runtime would take.

Local only. No API keys. Live network checks are optional.

## Commands

- `whichproxy HOST [HOST...]` — route for each host
- `whichproxy env` — print proxy-related environment variables
- `whichproxy doctor` — check well-known AI hosts + warn about dangerous NO_PROXY entries
- `whichproxy suggest` — print a safe NO_PROXY; does not write env
- `whichproxy --json` — machine-readable output

## Matching models

Evaluate each host against the same `NO_PROXY` list using three models:

1. **curl** — `*` matches all; `.example.com` matches subdomains of example.com
   (not `example.com` itself); exact token match; optional leading dot.
2. **python** — `urllib.request.proxy_bypass_environment` semantics (suffix match
   so `openai.com` matches `api.openai.com`).
3. **go** — `*` all; `example.com` matches that host and subdomains;
   `.example.com` matches subdomains only; CIDR for IPs when parseable.

If models disagree, mark the host `DISAGREE` and explain.

## Dangerous patterns (doctor)

Warn if `NO_PROXY` contains any of:
`openai.com`, `.openai.com`, `api.openai.com`, `chatgpt.com`, `.chatgpt.com`,
`auth.openai.com`, `x.ai`, `api.x.ai`, `auth.x.ai`, `anthropic.com`,
`api.anthropic.com`, `claude.ai`, `generativelanguage.googleapis.com`,
`cursor.com`, `cursor.sh`, `api2.cursor.sh`

These make Codex/ChatGPT token exchange bypass Clash.

## Output (text)

```
api.openai.com
  HTTP_PROXY=http://127.0.0.1:7897
  NO_PROXY=localhost,127.0.0.1,openai.com
  curl    DIRECT  (suffix openai.com)
  python  DIRECT  (suffix openai.com)
  go      DIRECT  (match openai.com)
```

## Privacy

Do not print full secrets. If a proxy URL has a user:password, redact the password.
Do not upload anything.
