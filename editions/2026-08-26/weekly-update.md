# AI Weekly · 2026-08-19 — 2026-08-25

本周真正值得带走的不是某个更大的模型，而是三个可以直接改变系统设计的机制：把“生成”和“验证”拆开；让结构化 markup 服务读取、让自然语言和 deterministic tests 服务写作；把来源与时效约束放进 search tool contract，而不是只写在 prompt 里。以下三个主题均通过时间窗口、primary source、反证、可复现实验和教学价值评审。

## 1. Search agent 的瓶颈可能是 selection，而不是 generation

**价值：** 当正确答案已经存在于 candidate pool 时，增加一个独立、会重新检索证据的 verifier，通常比继续升级 generator 更直接。

**Evaluation score：** 82.8/100

### 为什么是现在

AI21 在 8 月 19 日公布了一组 FACTS-Search 实验：固定 candidate pool 后，普通 majority vote 得分 83.3；换成会为每个候选独立执行 web research 的 verifier 后，vendor-reported score 达到 93.4。更关键的工程发现是 `pass@k` 明显高于 `pass@1`——生成器往往已经生成过正确答案，只是 aggregator 选错了。一个经过 SFT + RL 训练的 8B verifier 在相同 pool 上报告了 92.9，并显著降低验证成本。

这不是“所有任务都该训练 verifier”的结论。公开材料只覆盖两个 search QA benchmark、每个约 100 道题，而且核心成绩来自 AI21 自报；正确迁移是先测量自己的 `pass@k - pass@1` headroom，再决定 verifier 是否值得。

### 教学

把 search pipeline 拆成三个无共享 reasoning state 的阶段：

1. `Generator pool`：用便宜模型生成多个候选答案，并保存各自 citations。
2. `Verifier`：只接收 question + 单个 candidate，重新搜索，输出 `VALID | NOT_VALID | UNKNOWN`、证据和反证；不能看到其他候选的票数。
3. `Aggregator`：只在通过 verifier 的答案中聚合；如果没有答案通过则 abstain，而不是回退到原始多数票。

关键不是总体 verdict accuracy，而是按 question 计算四个指标：

- `pass@1`：随机/默认选择一个候选时正确率；
- `pass@k`：pool 中至少包含一个正确答案的比例，即 oracle ceiling；
- `pass@1(v)`：验证后 pool 的默认选择正确率；
- `pass@k(v)`：验证后仍至少保留一个正确答案的比例。

由此可分离三个问题：`verification lift = pass@1(v)-pass@1`、aggregator headroom，以及 verifier 错杀全部正确答案造成的 recall cap。训练或调 prompt 时必须同时看 precision 和 recall；只提升 veto precision 很容易把 pool 清空。

### Hands-on demo

1. 从自己的 production search logs 取 20 个已有 ground truth 的多跳问题，冻结 test set。
2. 对每题用同一个低成本 generator 采样 4 次，记录 `pass@1` 与 `pass@4`；若两者接近，先不要做 verifier。
3. 新建 verifier prompt：要求重新检索 primary source、寻找反例，并只返回结构化 verdict、citations 与 uncertainty。
4. 比较 `majority vote`、`frontier verifier` 和 `small verifier` 三种配置，禁止 verifier 读取投票分布。
5. 逐题统计四个 pass 指标、token cost、wall-clock latency 和 abstention rate；只有 quality/cost frontier 改善才上线。

### 适用 / 不适用

适用：

- 多跳 factual search、due diligence、entity resolution 等“验证窄于生成”的任务；
- 已观察到高 `pass@k`、低 `pass@1` 的系统；
- 可以获得 ground truth 或 executable verification 的场景。

不适用：

- 主观写作、审美判断或没有可核验真值的任务；
- 单次 generation，没有 candidate pool；
- verifier latency 高于业务 SLA 且无法并行的路径。

### Caveats

- AI21 数据是 vendor-reported，尚未找到完整训练代码、weights 或独立复现。
- 两个 benchmark 都只有约 100 个 evaluation questions，置信区间和 domain shift 需要自行重测。
- 自动 grader noise、SFT 对 closed model 的 distillation、额外 latency 均可能改变实际 economics。
- verifier 与 generator 必须隔离候选票数和共享 rationale，否则容易把验证退化成 confirmation。

### Sources

- https://www.ai21.com/blog/you-need-a-verifier/
- https://www.kaggle.com/benchmarks/google/facts

## 2. Structure for reading，prose and tests for writing

**价值：** 输入文档的结构化表达与生成指令的结构化表达不是同一问题；把 XML/JSON 的成功从 extraction 直接外推到 generation conditioning，可能显著降低质量。

**Evaluation score：** 80.8/100

### 为什么是现在

8 月 21 日提交的新论文研究了一个真实 tender-response multi-agent system。作者报告：把文档解析成带稳定 locator 的嵌套 markup，使三个 reading tasks 从不可复现变得稳定；但把写作 instruction 从 prose 改成 nested XML，在一个 paired comparison 中把 answer quality 从 74% 降到 48%。论文还观察到两个容易被忽略的 failure mode：

- prompt 中直接命名禁止出现的坏结构，可能反而向模型提供这些 tokens；96% 的残余缺陷集中在被明确命名的两类形式中。
- stochastic annotation 后接 deterministic windowing，会放大微小随机差异；同一输入中两个 slot 的差异最终变成 17 个 question 的差异。

最有用的 takeaway 不是“永远不要 XML prompt”，而是把 read path 和 write path 分开 A/B test：structure 用来保持输入的 containment、adjacency 和 locator；写作约束用自然 prose、positive requirements 和模型可执行的 output tests 表达。

### 教学

一个稳健 document agent 可以采用以下分层：

```text
source files
→ deterministic parser
→ ordered elements with stable eid/locator
→ structured extraction and requirement table
→ prose drafting instruction
→ deterministic output validators
→ human edit gate
```

结构化读取的目的，是让模型知道某个问题、说明、表格单元和 answer box 的相对关系，并能把输出追溯回原文位置。写作阶段则避免把所有规则嵌成深层 schema；给模型清晰 prose、正向描述和自检问题，然后用代码验证 page limit、required headings、numbers、citations 与 forbidden patterns。

当上游包含 stochastic step 时，不要直接让其结果决定 deterministic segmentation。先持久化 annotations，做 diff、置信度阈值和 invariant checks；否则很小的 annotation variance 会改变下游窗口数量和任务拓扑。

### Hands-on demo

1. 选一个含段落、表格和 instructions 的固定文档，解析为 `{eid, locator, text, parent, format_flags}`。
2. 固定 model、temperature、source context 与 20–30 个 questions，只改变 conditioning：A 组 nested XML instructions，B 组 concise prose instructions。
3. 两组都运行至少 10 次，统计 requirement coverage、unsupported claims、format violations 与 run-to-run variance。
4. 将“不要写 X/Y 坏结构”改为正向 self-test，例如“逐句检查是否有两个 independent claims；若有则拆分”。
5. 在 stochastic annotation 与 windowing 之间加入 persisted artifact 和 invariant：相同 source hash 必须得到相同 question count，差异则 fail closed。

### 适用 / 不适用

适用：

- tender、compliance、financial filing、research memo 等结构复杂且要求可追溯的 document agents；
- extraction 与 generation 同时存在的 multi-stage pipeline；
- 需要 human edit gate 和 deterministic validation 的正式文档。

不适用：

- 简短自由写作或没有复杂 source topology 的任务；
- 团队尚未建立固定 evaluation set，却准备一次性重写全部 prompts；
- 把单篇论文的数值直接当作跨模型普遍规律。

### Caveats

- 主要 paired comparison 只有一个 procurement、每组 `n=31`，尚未独立复现。
- ground-truth comparison 使用与 drafter 同一 model family 的单一 LLM judge，没有 blinded human scoring。
- 系统包含 43 个 single-shot roles，结论可能依赖其具体架构和 domain。
- 论文自己承认部分实验在 active development 中改变了多个变量；应把它视为强 experiment prompt，而不是定律。

### Sources

- https://arxiv.org/abs/2608.20786
- https://arxiv.org/pdf/2608.20786

## 3. Freshness 和 source policy 应进入 search tool contract

**价值：** 与其在 prompt 里请求“只查最近一周的官方来源”，更可靠的做法是让 search backend 在每次 tool call 上执行 domain allowlist 和 published-date bounds。

**Evaluation score：** 89.2/100

### 为什么是现在

Amazon Bedrock AgentCore 在 8 月 19 日发布 Web Search connector `1.2.0`，新增 request-level `domainFilter` 和 `publishedDateFilter`。这项更新本身只适用于 AgentCore，但背后的工程模式具有普适性：source governance 和 freshness 是 retrieval policy，不应只依赖模型是否记得遵守自然语言 instruction。

它采用两层策略：管理员在 target level 设置不可见的 include/exclude policy；agent 每次调用再缩小 domain 和 date window。两个 include lists 取交集，任一 exclude 命中即删除，request 不能扩大 admin policy。这是一个很实用的 `policy ceiling + per-task narrowing` 模型。

### 教学

把 search input 从单纯的 query 扩展成 typed contract：

```json
{
  "query": "AI engineering releases",
  "maxResults": 10,
  "filters": {
    "domainFilter": {
      "include": ["arxiv.org", "github.com", "docs.aws.amazon.com"],
      "exclude": ["medium.com"]
    },
    "publishedDateFilter": {
      "from": "2026-08-19T00:00:00Z",
      "to": "2026-08-25T23:59:59Z"
    }
  }
}
```

更通用的实现原则是：

- `admin policy` 定义永远不能越过的 source boundary；
- `task policy` 只能收窄，不能扩大；
- filter、query、returned publication date 和被拒绝结果数量都写入 audit log；
- prompt 仍解释“为什么需要这些来源”，但 enforcement 在 tool/backend；
- 没有结果时返回 empty/abstain，不允许模型静默取消 filters 再搜一次。

### Hands-on demo

1. 为现有 web search wrapper 增加 `include_domains`、`exclude_domains`、`published_from`、`published_to` typed fields。
2. 在 backend 层计算 `effective_include = admin_include ∩ request_include`，计算所有 exclude 的并集。
3. 用三个测试验证：request 不能越权扩大 domain；UTC 边界日被正确包含；零结果时不会自动放宽规则。
4. 对同一批 recent-news questions A/B 比较 prompt-only 与 enforced-filter 版本的 out-of-window rate 和 non-primary-source rate。
5. 将 effective policy 和 returned dates 写入 trace，让 evaluator 能区分“模型没遵守”与“search index metadata 错误”。

### 适用 / 不适用

适用：

- 新闻、价格、政策、release notes 等强时效任务；
- 法律、医疗、金融等需要 source allowlist 的研究；
- 多租户系统中不同客户拥有不同 approved domains。

不适用：

- index 没有可靠 publication metadata 的 corpus；
- exploratory research 需要最大 recall，而允许域列表尚不完整；
- 团队把 filter 当成 factuality guarantee，不再核验正文和 primary source。

### Caveats

- 当前参数和 zero-egress claims 是 AWS AgentCore 专有能力，不代表其他 search provider 自动具备相同行为。
- webpage 的 `publishedDate` 可能缺失、错误或把 updated date 当作 original date；filter 不能替代正文核验。
- 过窄 allowlist 会制造 silent recall loss，必须监控 empty-result rate 和 human overturn。
- 文档页面的 availability section 与同页其他区域存在 region 信息更新节奏差异，部署前应以账户/region 实测为准。

### Sources

- https://aws.amazon.com/blogs/machine-learning/domain-and-publish-date-filters-for-web-search-on-agentcore/
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html
