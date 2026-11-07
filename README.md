# envdiff

**对比两份环境变量配置，默认脱敏输出差异。**

部署前想知道 `.env.local` 和 `.env.prod` 到底差在哪，又不想把密钥打印到终端或 CI 日志里？`envdiff` 就做这一件事。

[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Zero deps](https://img.shields.io/badge/dependencies-0-brightgreen)](#设计取舍)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![CI](https://github.com/eathink/envdiff/actions/workflows/ci.yml/badge.svg)](https://github.com/eathink/envdiff/actions/workflows/ci.yml)

## 为什么需要它

环境变量配置的漂移是最常见的线上事故来源之一：新加的开关忘了同步、测试环境的值被带进生产、密钥轮换后只改了一边。`diff` 能看差异，但它会原样打印密钥；`grep` 能筛 key，但不告诉你值是否变了。

`envdiff` 的取舍：

- **只看差异，不做合并** —— 没有 `--write`，不修改任何文件，天然适合只读的 CI 环境
- **默认脱敏** —— 变量名像密钥（`*_TOKEN`、`*_PASSWORD`、`API_KEY` …）或值符合已知密钥格式（`ghp_`、`sk-`、`AKIA` …）都会被打码
- **脱敏仍可判断变化** —— 打码结果保留长度和 SHA-256 短指纹，能看出"变了"，但看不出原文
- **零依赖** —— 只用 Python 标准库，`pipx install` 后即用，不需要 venv 管理一堆传递依赖
- **退出码可当门禁** —— 有差异返回 1，可直接挂在部署流水线前面

## 安装

```bash
# 推荐：pipx，全局可用且隔离
pipx install git+https://github.com/eathink/envdiff

# 或者
pip install git+https://github.com/eathink/envdiff
```

要求 Python 3.10+。

## 用法

```bash
envdiff .env.local .env.prod
```

```console
对比 .env.local → .env.prod

  ~ API_URL       http://localhost:8000 → https://api.example.com
  ~ APP_ENV       local → production
  ~ DB_HOST       localhost → db.internal
  ~ DB_PASSWORD   <redacted:10c#e1c6aed0> → <redacted:11c#f5098d9c>
  ~ DEBUG         true → false
  - FEATURE_X     off
  + FEATURE_Y     on
  ~ GITHUB_TOKEN  <redacted:40c#ba94fef9> → <redacted:40c#218c83c4>

6 变更，1 新增，1 删除，0 未变
```

标记含义：`+` 新增、`-` 删除、`~` 值变化。默认只显示差异，`--all` 连未变化的变量一起列。

### 输出格式

```bash
envdiff .env.local .env.prod --format markdown   # 贴进 PR / Issue
envdiff .env.local .env.prod --format json       # 交给脚本处理
```

### 从标准输入读取

```bash
kubectl exec deploy/api -- printenv | envdiff - .env.prod
```

`-` 表示左值从 stdin 读取，按 `.env` 格式解析（`KEY=VALUE` 每行一个，`printenv` 的输出可直接用）。

### 只看部分变量

```bash
# 只对比 APP_ 前缀
envdiff .env.local .env.prod --include 'APP_*'

# 忽略调试类变量，避免它们触发门禁
envdiff .env.local .env.prod --exclude 'DEBUG*' --exclude '*_TRACE'
```

`--include` / `--exclude` 接收 glob，可重复，大小写敏感。过滤后的集合同时决定输出、统计和退出码——被排除的差异不会让命令返回 1。

### 退出码

| 码 | 含义 |
| --- | --- |
| 0 | 没有差异；或使用了 `--exit-zero` |
| 1 | 存在差异 |
| 2 | 输入无法读取或解析 |

```yaml
# CI 里当门禁
- run: envdiff .env.example .env.production --format markdown >> "$GITHUB_STEP_SUMMARY"
```

默认任何差异（新增 / 删除 / 变更）都返回 1。如果只想拦截危险变化：

```bash
# 只关心删除和值变更，新增变量不算失败
envdiff .env.local .env.prod --fail-on removed,changed

# 只输出报告，不计入门禁
envdiff .env.local .env.prod --fail-on none
```

`--exit-zero` 优先级最高，存在时永远返回 0。

### 选项

| 选项 | 说明 |
| --- | --- |
| `-f, --format {text,markdown,json}` | 输出格式，默认 `text` |
| `--all` | 同时显示未变化的变量 |
| `--include GLOB` | 只保留 key 匹配该 glob 的变量，可重复 |
| `--exclude GLOB` | 排除 key 匹配该 glob 的变量，可重复 |
| `--no-mask` | 输出原文（危险，仅本地调试；会向 stderr 打警告） |
| `--fail-on STATUSES` | 哪些差异导致退出码 1：`all`（默认）、`none` 或 `added,removed,changed` 的任意组合 |
| `--exit-zero` | 有差异也返回 0 |
| `--version` | 版本号 |

## 输入格式

- **`.env`** —— 支持 `export ` 前缀、单/双引号、`\n` 等转义、行内注释（`KEY=value # 注释`）
- **`.json`** —— 仅接受扁平对象，字符串/数字/布尔/null 会转成字符串比较；嵌套结构直接报错，避免隐式语义
- 扩展名决定解析方式，其他扩展名按 `.env` 处理

## 脱敏规则

满足任一条件即打码：

1. **变量名命中敏感词**：`SECRET`、`TOKEN`、`PASSWORD`、`PASSWD`、`PWD`、`API_KEY`、`PRIVATE_KEY`、`CREDENTIALS`、`ACCESS_KEY`、`AUTH_TOKEN`、`SESSION`（按 `_` 分词，`MONKEY` 不会误判）
2. **值命中已知格式**：GitHub token（`ghp_` / `github_pat_`）、OpenAI key（`sk-`）、AWS Access Key（`AKIA` / `ASIA`）、Google API key（`AIza`）、Slack token（`xox[baprs]-`）、JWT、PEM 私钥头

打码格式为 `<redacted:{长度}c#{sha256前8位}>`。长度和指纹都来自原值，所以同一份配置重复运行结果稳定，两次打码结果不同就说明值确实变了。

## 设计取舍

- **不读进程环境变量**：只比较显式给出的文件，避免"我这台机器上能跑"的隐式依赖
- **不做嵌套 JSON 展开**：`{"db": {"host": "x"}}` 会报错而不是自动压成 `db.host`，因为不同工具的展开规则不一致，静默猜测比报错更危险
- **不写回、不合并**：合并策略（谁优先、要不要保留注释）是个无底洞，交给用户自己决定
- **保持零依赖**：这个工具的定位是"在最小环境里也能跑"，包括没有 pip 的系统

## 开发

```bash
git clone https://github.com/eathink/envdiff
cd envdiff

# 仅用标准库，无需安装依赖
PYTHONPATH=src python3 -m unittest discover -s tests -v

# 本地运行
PYTHONPATH=src python3 -m envdiff path/to/left.env path/to/right.env
```

## License

[MIT](LICENSE)
