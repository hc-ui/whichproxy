# whichproxy

看一个主机是走你的 HTTP(S) 代理，还是被 `NO_PROXY` 放行直连。

[English](README.md) · [简体中文](README.zh-CN.md)

## 为什么要有这个工具

**Windows + Clash** 上，Codex / Claude 一类 CLI 经常踩同一个坑： **浏览器** 能走代理登录，**CLI** 却 `403` *country, region, or territory not supported*。

常见原因是 `NO_PROXY` 里写了 `openai.com` 或 `chatgpt.com`。浏览器仍走 Clash，CLI 换 token 时直连国内出口。不同运行时对 `NO_PROXY` 的匹配还不一致（`.openai.com` 和 `openai.com` 含义不同）。

`whichproxy` 打印 **curl**、**Python**、**Go** 各自会走的路由。它自己不发任何请求。

## 警告

> [!WARNING]
> **不要**把 `openai.com`、`.openai.com`、`api.openai.com`、`auth.openai.com`、`chatgpt.com`、`.chatgpt.com` 写进 `NO_PROXY`。
>
> 这会让 Codex / ChatGPT 换 token 绕过 Clash。
>
> `NO_PROXY` 只留本机地址，例如：
>
> ```text
> localhost,127.0.0.1,::1
> ```

## 安装

需要 **Python 3.10+**。包名是 **`whichproxy`**。尚未发布到 PyPI，请从克隆下来的源码安装：

```bash
pip install -e .
```

安装后即可使用 `whichproxy` 命令。

## 20 秒上手

错误的 `NO_PROXY`（Windows + Clash 上最常见的坑）：

```powershell
$env:HTTP_PROXY  = "http://127.0.0.1:7897"
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
$env:NO_PROXY    = "localhost,127.0.0.1,openai.com"
whichproxy api.openai.com
```

POSIX：

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

curl 对无前导点的 token 只做精确匹配；Python 和 Go 把 `openai.com` 当后缀。该主机会标成 `DISAGREE`。

## 命令

| 命令 | 作用 |
| --- | --- |
| `whichproxy HOST [HOST...]` | 按 curl / python / go 打印每个主机的路由 |
| `whichproxy env` | 打印与代理相关的环境变量 |
| `whichproxy doctor` | 检查常见 AI 主机，并对危险的 `NO_PROXY` 项告警 |
| `whichproxy --json` | 同样的结果，机器可读输出 |

`env` / `doctor` 会读取 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY`（以及小写别名）。

## 三种匹配器

同一份 `NO_PROXY`，三种模型。核心差别就是有没有前导点：

| 模型 | 匹配规则 | `openai.com`（无点） | `.openai.com`（前导点） |
| --- | --- | --- | --- |
| **curl** | `*` = 全部；无点 = **精确**匹配；前导 `.` = **仅子域** | 只匹配 `openai.com`，**不**匹配 `api.openai.com` | 匹配 `api.openai.com`，**不**匹配 `openai.com` 本身 |
| **python** | `urllib.request.proxy_bypass_environment` — **后缀**匹配 | `openai.com` **和** `api.openai.com` | 遵循 urllib（去掉前导 `.` 后再做后缀匹配） |
| **go** | `*` = 全部；无点 = 该主机**及其子域**；前导 `.` = **仅子域**；IP 支持 CIDR | `openai.com` **和** `api.openai.com` | 匹配 `api.openai.com`，**不**匹配 `openai.com` 本身 |

不一致时标为 `DISAGREE`，并给出每个模型的原因。

## 隐私

- **仅本地。** 只读环境变量。不发网络请求，不要 API key，不上传任何内容。
- 代理 URL 里若有 `user:password`，输出中会打码密码。

## 许可证

[MIT](LICENSE)
