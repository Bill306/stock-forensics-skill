# 股票 Forensics Skill

这是一个用于反向研究股票历史驱动因素的 Agent Skill：从重大股价波动出发，追溯当时的事件、市场预期和核心经营指标。

[English README](README.md)

## 解决什么问题

价格图只能告诉我们股票何时发生波动，却不能说明哪些预期改变、哪些证据真正重要。这个 Skill 提供一套可复用的方法，将重大波动与有日期的来源及公司特定经营指标连接起来，同时避免把时间上的重合直接写成未经证实的因果关系。

## 能做什么

- 将重大股价波动与有日期、有来源的催化剂对应起来；
- 用大盘和行业基准区分共同波动与公司新闻候选，并串联首次披露和后续更新；
- 找出市场反复定价的一至两个核心指标；
- 对比实际业绩、同期一致预期和业绩后股价反应；
- 追踪多季度电话会中分析师问题与管理层语气的变化；
- 生成证据分层的研究报告和可选的交互式 HTML 图表；
- 区分公司披露、市场数据、分析推断和尚未解决的数据缺口。

仓库附带一个可选的本地 Flask 应用，通过 `yfinance` 获取 Yahoo Finance 数据并生成基础图表。它只是便利工具，不能替代公司公告、交易所文件、业绩电话会及经过核验的原始来源。

## 本地 v1.3.0 更新

新增电话会证据与预期校验、四级归因、反例检查，以及公司新闻、宏观/行业新闻和首次披露时间线字段。收益工具支持同时对比多个命名基准，例如大盘 ETF 和行业 ETF。ETF 涨跌只反映价格背景；声称资金流入/流出需另有资金流数据。新闻、行业基准和资金流数据仍需人工检索并附来源，应用不会自动抓取新闻。这里的版本号表示本地工作副本，不表示 GitHub 已更新。

## 本地 v1.4.0 更新

扩展了新闻/事件普查规则：公司自身生成的内容也算候选事件，包括例行的业绩日期通知、招股补充文件或股份解禁资格披露、公司发布的产品或研究公告，只要与筛选出的异动日重合。此类事件在时间和内容证据不足时最高只标记为 `coincident_only`；披露日与市场反应日分开记录；具备出售资格不等于股东实际卖出；普查完整度以"已映射/未匹配异动日"计数（例如 46 个异动日中 26 个有来源事件）。同时记录了自包含交互 HTML 图表模式：可点击事件标记与详情面板、有/无事件筛选、默认五年视图加可选区间、相对基准收益以 % 标注、logo 等素材 base64 内嵌以支持离线打开，以及基于可用逐字稿的卖方提问焦点迁移模块（定性归纳、披露覆盖季度、不做频次统计伪装）。GitHub 发布是单独的一步。

电话会脚本校验分析者写出的 JSON，不自动转录、阅读电话会、核验原文真实性或判断股价驱动。

```bash
python3 scripts/transcript_forensics.py validate --input examples/transcript-only.json
python3 scripts/transcript_forensics.py price-window --prices examples/daily-prices.json --benchmark examples/daily-benchmark.json --event-date 2026-09-30 --timing after-close
python3 scripts/transcript_forensics.py price-window --prices examples/daily-prices.json --event-date 2026-09-30 --timing after-close --benchmark QQQ=examples/daily-benchmark.json --benchmark XLK=examples/daily-industry-benchmark.json
python3 scripts/transcript_forensics.py export-events --input examples/transcript-only.json --prices examples/daily-prices.json
```

示例均为虚构数据；JSON 的 `--output` 拒绝覆盖已有文件。详见 [证据结构](references/evidence-schema.md)、[收益口径](references/event-windows.md)、[电话会流程](references/transcript-forensics.md) 和 [新闻与市场背景流程](references/news-and-market-context.md)。校验通过只表示结构与归因资格一致，不证明事实或因果关系成立。

图表 API `/api/generate` 可以接收 `{"symbol":"TICKER","evidence":{...}}`，先验证证据并核对股票代码，再展示时间、归因等级和来源/引文位置。未经核验历史截点的供应商预期不能支持最高归因等级。

## 安装 Skill

先克隆仓库：

```bash
git clone https://github.com/Bill306/stock-forensics-skill.git
```

再将整个仓库目录复制或软链接到你的 Agent 所支持的 Skills 目录，确保客户端能够发现根目录的 `SKILL.md`。不同客户端的安装路径可能不同。

## 使用

如果请求没有指定分析期间，Skill 默认使用截至最近一个完整交易日的过去五年。用户可以指定其他年限或自定义起止日期。图表默认显示 5Y，并可切换至 1Y、2Y、3Y、10Y 或全部可用历史。

调用示例：

```text
使用 $forensics 分析 NVDA 的股价驱动因素；如无特别指定，使用默认的过去五年区间。
区分已核验催化剂与分析推断，找出核心指标，并引用原始来源。
```

## 输入与输出

输入股票代码、可选研究区间和可用资料后，Skill 会引导 Agent 产出：

1. 聚焦重大波动的价格历史摘要；
2. 业绩 Forensics 表格；
3. 主要与次要股价驱动指标；
4. 可证伪的多空核心争议；
5. 不同市场特征的说明；
6. 可选的自包含 HTML 催化剂图表。

示例输入：

```text
分析 700.HK 在 2023 至 2025 年间的最大股价波动，解释重要指标，
并将无法取得的一致预期数据明确标为 unavailable。
```

示例输出结构：

```text
股价波动：[日期区间与幅度]
已核验催化剂：[事件、原始来源及发布日期]
核心指标：[指标与证据]
分析判断：[明确标注为 inference]
数据缺口：[unavailable 或尚未解决的项目]
```

以上只是输出结构示例，不构成对腾讯或任何证券的事实陈述。

## 可选本地图表应用

建议使用 Python 3.9 或更高版本：

演示：本项目没有托管在线 Demo。可以按照下列步骤在本机运行股票搜索和图表生成器。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/server.py
```

打开 `http://127.0.0.1:3457`。生成的图表默认保存到 `./forensics-output`。

| 环境变量 | 默认值 | 用途 |
|---|---|---|
| `FORENSICS_HOST` | `127.0.0.1` | HTTP 监听地址 |
| `FORENSICS_PORT` | `3457` | 本地端口 |
| `FORENSICS_OUTPUT_DIR` | `./forensics-output` | 图表输出目录 |

应用没有身份验证功能。除非另行增加访问控制并完成部署安全审查，否则应保持本机监听。

## 验证

```bash
./scripts/validate.sh
```

验证脚本会编译 Python 服务，并测试股票代码校验、输出路径限制和 HTML/脚本转义。它不能证明 Yahoo Finance 始终可用，也不能证明研究结论正确。

## 数据与研究边界

- `yfinance` 是非官方数据适配器，其字段、复权方式、可用性和历史覆盖可能变化。
- 一致预期与业绩后反应需要匹配当时的可靠来源；缺失值不得编造。
- 股价与事件在时间上的对应只提供研究假设，不能单独证明因果关系。
- HTML 在线时会加载 Google Fonts；离线时使用系统回退字体，核心图表仍可使用。
- 输出质量取决于所提供资料的质量与完整性。
- 输出仅用于研究，不构成个性化投资建议或交易执行。

## 安全与许可证

安全报告方式见 [SECURITY.md](SECURITY.md)。请勿提交券商数据、专有研报、API 凭证、用户持仓或客户生成材料。

项目采用 MIT License，Copyright (c) 2026 Bill306。详见 [LICENSE](LICENSE)。
