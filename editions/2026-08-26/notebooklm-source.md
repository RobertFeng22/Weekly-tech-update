# NotebookLM Source Pack: AI Weekly 2026-08-19 — 2026-08-25

本文件仅包含通过 evaluation gates 的三个主题。Video Overview 必须区分 source fact、作者主张与我们的工程 inference；不得把 vendor-reported benchmark 当作独立复现。

## Topic 1: Search agent 的瓶颈可能是 selection，而不是 generation

Evaluation score: 82.8/100

AI21 8 月 19 日公布的 FACTS-Search 实验提出：在 agentic search 中，candidate pool 经常已经包含正确答案，主要错误来自 aggregator 选错。固定 pool 后，majority vote 的 vendor-reported score 为 83.3；为每个候选独立重新执行 web research 的 frontier verifier 报告 93.4。AI21 的 SFT + RL 8B verifier 报告 92.9，并把验证成本显著降低。

工程架构是 `generators → independent verifier per candidate → aggregate verified candidates only`。Verifier 不能看到票数或其他候选 rationale；它只接收 question 和一个 candidate，独立检索 primary evidence，返回 `VALID | NOT_VALID | UNKNOWN`。如果所有候选都被否决，系统 abstain。

评估必须按 question 统计 `pass@1`、`pass@k`、`pass@1(v)` 和 `pass@k(v)`。`pass@k-pass@1` 测量 selection headroom；`pass@1(v)-pass@1` 测量 verification lift；`pass@k-pass@k(v)` 测量 verifier 错杀全部正确答案造成的 recall loss。若自己的 `pass@k` 与 `pass@1` 很接近，增加 verifier 可能只有成本，没有收益。

### Demo script

1. 冻结 20 个有 ground truth 的多跳 search questions。
2. 用同一低成本 generator 每题采样四个 candidates，记录 pass@1/pass@4。
3. 建立隔离 verifier，逐候选重新搜索并输出 verdict、citations、counter-evidence。
4. 比较 majority vote、frontier verifier、small verifier 的 quality/cost/latency。
5. 监控 abstention 和 verifier recall cap，只有 Pareto frontier 改善才部署。

### Limitations

- AI21 成绩是 vendor-reported，未找到完整独立复现、weights 或训练代码。
- evaluation sample 约 100 questions，且训练 labels 带 automated-grader noise。
- 方法最适合 factual search，不应直接迁移到主观写作。

### Source URLs

- https://www.ai21.com/blog/you-need-a-verifier/
- https://www.kaggle.com/benchmarks/google/facts

### Video steering prompt

生成简体中文 Explainer。先用一个“多数人都答错，但少数 candidate 已经答对”的例子解释 selection bottleneck，再画出 generator pool、独立 verifier、verified-only aggregator 三层流程。重点教学四个 pass 指标以及 verifier precision/recall trade-off。明确所有分数均为 AI21 vendor-reported，样本约 100 题，不能称为独立复现。结尾给出 20-question A/B demo，不讨论泛化的 AGI 结论。

## Topic 2: Structure for reading，prose and tests for writing

Evaluation score: 80.8/100

8 月 21 日的新论文研究真实 tender-response agent。作者报告：将输入解析成带 stable `eid/locator` 的 nested markup，显著改善三个 reading tasks；但把写作 instructions 从 prose 改成 nested XML，在单一 paired comparison 中将 quality 从 74% 降到 48%。论文还观察到，直接在 prompt 中命名禁止形式可能集中残余缺陷，以及 stochastic annotation 接 deterministic windowing 会放大微小 variance。

稳健架构应是：`deterministic parsing → structured reading/extraction → persisted requirements → prose drafting instruction → deterministic output validators → human gate`。Structure 负责保存 containment、adjacency 与 provenance；写作规则用正向 prose 和 self-tests 表达；硬约束由代码验证。

### Demo script

1. 将固定文档解析成 `{eid, locator, text, parent, format_flags}`。
2. 固定所有条件，只 A/B 测试 nested XML instructions 与 concise prose instructions。
3. 每组运行 10 次以上，统计 coverage、unsupported claims、format violations 和 variance。
4. 把“不要写坏模式 X”改成模型可执行的正向逐句 self-test。
5. 在 stochastic annotation 后持久化 artifact，并用 source hash/question count invariant fail closed。

### Limitations

- 核心 paired comparison 来自一个 procurement、每组 `n=31`，未独立复现。
- human comparison 使用同 model family 的单一 LLM judge，没有 blinded human scoring。
- 结论是值得复现实验的 boundary，不是“XML prompt 永远更差”的定律。

### Source URLs

- https://arxiv.org/abs/2608.20786
- https://arxiv.org/pdf/2608.20786

### Video steering prompt

生成简体中文 Explainer。用左右分屏对比 read path 与 write path：左边展示 nested document markup 如何保存 table/paragraph containment 和 locator；右边展示为什么深层 XML instructions 可能压低 generation quality，并由 prose + positive self-tests + deterministic validators 替代。准确呈现 74%→48%、96% 和 2-slot→17-question 三个作者报告的结果，同时用醒目 caveat 标注单一 procurement、n=31、同家族 LLM judge 和未复现。最后给出可操作 A/B test。

## Topic 3: Freshness 和 source policy 应进入 search tool contract

Evaluation score: 89.2/100

Amazon Bedrock AgentCore 8 月 19 日发布 Web Search connector 1.2.0，支持 request-level domain include/exclude 和 inclusive ISO-8601 UTC publication-date bounds。管理员 target-level policy 与 request-level filters 组合：include 取交集、exclude 取并集，request 不能扩大 admin policy。

可迁移的核心不是 AWS 产品，而是 `policy ceiling + per-task narrowing`：强时效或高风险 research 不应只靠 prompt 说“查最近一周官方来源”，而应让 search backend 执行 typed constraints，记录 effective policy、returned publication dates 和 rejected-result counts；零结果时 fail closed，不能让模型静默取消 filters。

### Demo script

1. 为 search wrapper 添加 typed `include_domains/exclude_domains/published_from/published_to`。
2. 在 backend 计算 admin 与 request policy 的有效交集/并集。
3. 测试 request 不能越权、UTC 边界 inclusive、零结果不会自动放宽。
4. A/B 比较 prompt-only 与 enforced-filter 的越界日期率和非 primary-source 率。
5. 记录 empty-result rate，防止 allowlist 过窄导致 silent recall loss。

### Limitations

- 参数与 zero-egress 是 AWS 专有实现；其他 provider 需自行实现。
- publication metadata 可能错误，filter 不能替代打开正文核验。
- 过窄 policy 会降低 recall，必须有 abstention 与监控。

### Source URLs

- https://aws.amazon.com/blogs/machine-learning/domain-and-publish-date-filters-for-web-search-on-agentcore/
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html

### Video steering prompt

生成简体中文 Explainer。先演示 prompt-only 的 agent 如何忘记“最近一周+官方来源”，再展示 typed search contract。用图解释 admin policy 是 ceiling、request filter 只能 narrowing：include 取交集、exclude 取并集、date bounds 为 inclusive UTC。给出一个 JSON tool-call 示例和三个 deterministic tests。明确 AWS connector 1.2.0 是具体实现，通用原则才是教学重点；提醒 publication metadata error 与 recall loss。
